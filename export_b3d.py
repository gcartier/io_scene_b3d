import bpy

import os
import sys
import math
import mathutils
import datetime

def export_b3d(operator, b3d):
    with open(b3d, "w", encoding="utf-8", newline="\n") as file:
        def format(str):
            file.write(str)
        
        start_time = datetime.datetime.now()
        
        context = bpy.context
        scene = context.scene
        object = context.object
        armature = object.parent
    
        def is_object_instance_from_selected(object_instance):
            if object_instance.parent:
                return object_instance.parent.original.select_get()
            else:
                return object_instance.object.original.select_get()
        
        def selected_object_instance():
            depsgraph = context.evaluated_depsgraph_get()
            for object_instance in depsgraph.object_instances:
                if is_object_instance_from_selected(object_instance):
                    return object_instance
        
        def mesh_triangulate(mesh):
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(mesh)
            bm.free()

        # object
        format("OBJECT\n")
        object_name = object.name
        object_base = os.path.splitext(object_name)[0]
        format('"%s", %.3f, %.3f, %.3f, %.3f\n' % (object_base, scene.render.fps, scene.frame_start, scene.frame_end, scene.frame_current))
        
        object_instance = selected_object_instance()
        mesh = object_instance.object.to_mesh()
        mesh_triangulate(mesh)
        
        # vertices
        format("\nVERTICES\n")
        format("%i\n" % len(mesh.vertices))
        matrix_basis = object.matrix_basis
        for vert in mesh.vertices:
            group = -1
            weight = 0.
            for groupelem in vert.groups:
                if groupelem.weight > weight:
                    group = groupelem.group
                    weight = groupelem.weight
            co = matrix_basis @ vert.co
            normal = vert.normal
            index = -1
            if group != -1:
                name = object.vertex_groups[group].name
                index = armature.data.bones.find(name)
            format("%.6f, %.6f, %.6f, %.6f, %.6f, %.6f, %i\n" % (co.x, co.y, co.z, normal.x, normal.y, normal.z, index))
        
        # triangles
        format("\nTRIANGLES\n")
        format("%i\n" % len(mesh.polygons))
        uv_loops = mesh.uv_layers.active.data
        for poly in mesh.polygons:
            v1, v2, v3 = poly.vertices
            # hack around poly.material_index being 0 even when no material
            if len(object.material_slots) == 0:
                mat = -1
            else:
                mat = poly.material_index
            uv1 = uv_loops[poly.loop_start].uv
            uv2 = uv_loops[poly.loop_start + 1].uv
            uv3 = uv_loops[poly.loop_start + 2].uv
            format("%i, %i, %i, %i, %.6f, %.6f, %.6f, %.6f, %.6f, %.6f\n" %
                (v1, v2, v3, mat, uv1[0], 1.0 - uv1[1], uv2[0], 1.0 - uv2[1], uv3[0], 1.0 - uv3[1]))
        
        # materials
        format("\nMATERIALS\n")
        format("%i\n" % len(object.material_slots))
        for material_slot in object.material_slots:
            material = material_slot.material
            if not material.node_tree:
                format('"%s", ""\n' % (material_slot.name))
            else:
                def find_tex_image_node():
                    for node in material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            return node
                    return None
                
                node = find_tex_image_node()
                if not node:
                    format('"%s", ""\n' % (material_slot.name))
                else:
                    # remove starting //
                    filename = os.path.split(node.image.filepath)[1]
                    format('"%s", "%s"\n' % (material_slot.name, filename))
        
        # bones
        format("\nBONES\n")
        if not armature or armature.type != 'ARMATURE':
            format("0\n")
            format("\nANIMATIONS\n")
            format("0\n")
        else:
            class BoneExport:
                def __init__(self, prefix, bone):
                    self.prefix = prefix
                    self.bone = bone
                    self.locations = {}
                    self.euler_rotations = {}
                    self.quaternion_rotations = {}
                
                def __repr__(self):
                    return "BoneExport(%s)" % self.prefix
            
            def collect_boneexports():
                boneexports = []
                for bone in armature.data.bones:
                    prefix = 'pose.bones["%s"]' % bone.name
                    boneexport = BoneExport(prefix, bone)
                    boneexports.append(boneexport)
                return boneexports
            
            def get_boneexport(name):
                for boneexport in boneexports:
                    if boneexport.name == name:
                        return boneexport
                return None
            
            def find_boneexport(data_path):
                for idx, boneexport in enumerate(boneexports):
                    if data_path.startswith(boneexport.prefix):
                        return boneexport
                return None
            
            def compute_matrix(bone):
                parent_bone = bone.parent
                if not parent_bone:
                    base_bone_correction = mathutils.Matrix.Rotation(math.pi / 2, 4, 'Z')
                    return base_bone_correction @ bone.matrix_local
                else:
                    return parent_bone.matrix_local.inverted() @ bone.matrix_local
            
            boneexports = collect_boneexports()
            format("%i\n" % len(boneexports))
            for boneexport in boneexports:
                bone = boneexport.bone
                parent_bone = bone.parent
                parent_name = "" if (parent_bone is None) else parent_bone.name
                matrix = compute_matrix(bone)
                pos = matrix.to_translation()
                rot = matrix.to_euler('XYZ')
                length = bone.length
                format('"%s", "%s", %.6f, %.6f, %.6f, %.6f, %.6f, %.6f, %.3f\n' %
                    (bone.name, parent_name, pos[0], pos[1], pos[2], rot[0], rot[1], rot[2], length))
            
            # animations
            format("\nANIMATIONS\n")
            if not armature or not armature.animation_data or not armature.animation_data.action:
                format("0\n")
            else:
                action = armature.animation_data.action
                format("1\n")
                format('"%s"\n' % action.name)
                for fcurve in action.fcurves:
                    data_path = fcurve.data_path
                    boneexport = find_boneexport(data_path)
                    dict = None
                    if data_path.endswith("location"):
                        dict = boneexport.locations
                        kind = 'location'
                    elif data_path.endswith("rotation_euler"):
                        dict = boneexport.euler_rotations
                        kind = 'euler_rotation'
                    elif data_path.endswith("rotation_quaternion"):
                        dict = boneexport.quaternion_rotations
                        kind = 'quaternion_rotation'
                    if dict is not None:
                        for keyframe in fcurve.keyframe_points:
                            time = keyframe.co[0]
                            value = keyframe.co[1]
                            entry = dict.get(time)
                            if entry is None:
                                if kind == 'location':
                                    entry = [0., 0., 0.]
                                    dict[time] = entry
                                elif kind == 'euler_rotation':
                                    entry = [0., 0., 0.]
                                    dict[time] = entry
                                elif kind == 'quaternion_rotation':
                                    entry = [0., 0., 0., 0.]
                                    dict[time] = entry
                            entry[fcurve.array_index] = value
            for boneexport in boneexports:
                bone = boneexport.bone
                format('"%s"\n' % bone.name)
                locations = boneexport.locations
                euler_rotations = boneexport.euler_rotations
                quaternion_rotations = boneexport.quaternion_rotations
                format("%i\n" % len(locations))
                for time in sorted(locations):
                    loc = locations[time]
                    format("%.3f, %.6f, %.6f, %.6f\n" % (time, loc[0], loc[1], loc[2]))
                for time in sorted(quaternion_rotations):
                    rot = quaternion_rotations[time]
                    euler = mathutils.Quaternion(rot).to_euler('XYZ')
                    euler_rotations[time] = (euler.x, euler.y, euler.z)
                format("%i\n" % len(euler_rotations))
                for time in euler_rotations:
                    rot = euler_rotations[time]
                    format("%.3f, %.6f, %.6f, %.6f\n" % (time, rot[0], rot[1], rot[2]))
        
        # cleanup
        # this crashes blender
        # object_instance.object.to_mesh_clear()
        
        # report
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        print("Exported", "in", elapsed_time)

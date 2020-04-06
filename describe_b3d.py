import bpy

import os
import sys
import math
import mathutils

def describe():
    def format(str):
        sys.stdout.write(str)
    
    target_vertices = 0
    target_triangles = 0
    target_materials = 0
    target_bones = None
    target_frames = None
    
    context = bpy.context
    scene = context.scene
    object = context.object
    armature = object.parent
    
    if object.name == '_Idle.ms3d.mo':
        target_bones = ("Bone_0", "Bone_1", "Bone_3", "Bone_6", "Bone_13", "Bone_24", "Bone_31")
        target_frames = (0., 50., 100.)
    
    if object.type == 'MESH':
        def mesh_triangulate(me):
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        
        print()
        print()
        print()
        
        # armature
        format("ARMATURE\n")
        print(armature.matrix_local)
        print(armature.matrix_basis)
        
        # object
        format("\nOBJECT\n")
        format('"%s", %.3f, %.3f, %.3f, %.3f\n' % (object.name, scene.render.fps, scene.frame_start, scene.frame_end, scene.frame_current))
        print(object.matrix_local)
        print(object.matrix_basis)
        
        mesh = object.data
        mesh_triangulate(mesh)
        
        # vertices
        format("\nVERTICES %i\n" % len(mesh.vertices))
        matrix_basis = object.matrix_basis
        for rank, vert in enumerate(mesh.vertices):
            if rank < target_vertices:
                group = -1
                weight = 0.
                for groupelem in vert.groups:
                    if groupelem.weight > weight:
                        group = groupelem.group
                        weight = groupelem.weight
                co = matrix_basis @ vert.co
                index = -1
                if group != -1:
                    name = object.vertex_groups[group].name
                    index = armature.data.bones.find(name)
                format("%.6f, %.6f, %.6f, %i\n" % (co.x, co.y, co.z, index))
        
        # triangles
        format("\nTRIANGLES %i\n" % len(mesh.polygons))
        uv_loops = mesh.uv_layers.active.data
        for rank, poly in enumerate(mesh.polygons):
            if rank < target_triangles:
                v1, v2, v3 = poly.vertices
                n = poly.normal
                mat = poly.material_index
                uv1 = uv_loops[poly.loop_start].uv
                uv2 = uv_loops[poly.loop_start + 1].uv
                uv3 = uv_loops[poly.loop_start + 2].uv
                format("%i, %i, %i, %.3f, %.3f, %.3f, %i, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f\n" %
                    (v1, v2, v3, n.x, n.y, n.z, mat, uv1[0], 1.0 - uv1[1], uv2[0], 1.0 - uv2[1], uv3[0], 1.0 - uv3[1]))
        
        # materials
        format("\nMATERIALS %i\n" % len(object.material_slots))
        for rank, material_slot in enumerate(object.material_slots):
            if rank < target_materials:
                material = material_slot.material
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        # remove starting //
                        filename = os.path.split(node.image.filepath)[1]
                        format('"%s", "%s"\n' % (material_slot.name, filename))
        
        if armature.type == 'ARMATURE':
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
            
            # bones
            def compute_matrix(bone):
                parent_bone = bone.parent
                if not parent_bone:
                    return bone.matrix_local
                else:
                    return parent_bone.matrix_local.inverted() @ bone.matrix_local
            
            boneexports = collect_boneexports()
            format("\nBONES %i\n" % len(boneexports))
            for boneexport in boneexports:
                bone = boneexport.bone
                parent_bone = bone.parent
                parent_name = "" if (parent_bone is None) else parent_bone.name
                matrix = compute_matrix(bone)
                pos = matrix.to_translation()
                rot = matrix.to_euler('XYZ')
                length = bone.length
                #if target_bones is None or bone.name in target_bones:
                if not parent_bone:
                    format('%s, %s\n' % (bone.name, parent_name))
                    format('  %.3f, %.3f, %.3f\n' % (pos[0], pos[1], pos[2]))
                    format('  %.3f, %.3f, %.3f\n' % (rot[0], rot[1], rot[2]))
            
            # animations
            format("\nANIMATIONS 1\n")
            action = armature.animation_data.action
            if action is None:
                print("***** NO ACTION FOUND")
                return
            if action is not None:
                format('"%s"\n' % action.name)
                for fcurve in action.fcurves:
                    data_path = fcurve.data_path
                    boneexport = find_boneexport(data_path)
                    if boneexport is None:
                        print("***** FCURVE NOT FOUND", data_path)
                        return
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
                if target_bones is None or bone.name in target_bones:
                    format('"%s"\n' % bone.name)
                    locations = boneexport.locations
                    euler_rotations = boneexport.euler_rotations
                    quaternion_rotations = boneexport.quaternion_rotations
                    for time in sorted(locations):
                        if target_frames is None or time in target_frames:
                            loc = locations[time]
                            format("  %.3f Vertex %.3f, %.3f, %.3f\n" % (time, loc[0], loc[1], loc[2]))
                    for time in euler_rotations:
                        if target_frames is None or time in target_frames:
                            rot = euler_rotations[time]
                            format("  %.3f Euler %.3f, %.3f, %.3f\n" % (time, rot[0], rot[1], rot[2]))
                    for time in sorted(quaternion_rotations):
                        if target_frames is None or time in target_frames:
                            rot = quaternion_rotations[time]
                            format("  %.3f Quaternion %.3f, %.3f, %.3f, %.3f\n" % (time, rot[0], rot[1], rot[2], rot[3]))

describe()

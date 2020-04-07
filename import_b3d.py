import bpy
import os
import sys
import ast
import math
import mathutils
import datetime

def import_b3d(operator, b3d):
    dirname = os.path.dirname(b3d)
    with open(b3d, "r", encoding="utf-8", newline="\n") as file:
        def rline():
            return file.readline()
        
        def rliteral():
            return ast.literal_eval(file.readline())
        
        start_time = datetime.datetime.now()
        
        context = bpy.context
        scene = context.scene
        
        # name
        rline()
        info = rliteral()
        name = info[0]
        
        scene.render.fps = info[1]
        scene.frame_start = info[2]
        scene.frame_end = info[3]
        scene.frame_set(info[4])
        
        vertices_info = []
        triangles_info = []
        materials_info = []
        
        # vertices
        rline()
        rline()
        num_vertices = rliteral()
        for n in range(0, num_vertices):
            vert = rliteral()
            vertices_info.append(vert)
        
        # triangles
        rline()
        rline()
        num_triangles = rliteral()
        for n in range(0, num_triangles):
            tri = rliteral()
            triangles_info.append(tri)
        
        # materials
        rline()
        rline()
        num_materials = rliteral()
        for n in range(0, num_materials):
            mat = rliteral()
            materials_info.append(mat)
        
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(mesh.name, mesh)
        col = bpy.data.collections.get("Collection")

        verts = list(map(lambda vert: (vert[0], vert[1], vert[2]), vertices_info))
        edges = []
        faces = list(map(lambda tri: (tri[0], tri[1], tri[2]), triangles_info))

        mesh.from_pydata(verts, [], faces)
        
        uv_layer = mesh.uv_layers.new(name='UVMap', do_init=False)
        uv_loops = uv_layer.data
        
        for n in range(len(mesh.polygons)):
            poly = mesh.polygons[n]
            tri_info = triangles_info[n]
            poly.material_index = tri_info[3]
            uv_loops[poly.loop_start].uv = (tri_info[4], 1.0 - tri_info[5])
            uv_loops[poly.loop_start + 1].uv = (tri_info[6], 1.0 - tri_info[7])
            uv_loops[poly.loop_start + 2].uv = (tri_info[8], 1.0 - tri_info[9])
        
        col.objects.link(obj)
        context.view_layer.objects.active = obj

        for n in range(num_materials):
            mat_info = materials_info[n]
            mat = bpy.data.materials.new(name=mat_info[0])
            mat.use_nodes = True
            mat_nodes = mat.node_tree.nodes
            mat_links = mat.node_tree.links
            output = mat_nodes['Material Output']
            principled = mat_nodes['Principled BSDF']
            
            teximg = mat_nodes.new('ShaderNodeTexImage')
            teximg.image = bpy.data.images.load(dirname + "/" + mat_info[1])
            
            mat_links.new(teximg.outputs['Color'], principled.inputs['Base Color'])
            
            bpy.ops.object.material_slot_add()
            obj.material_slots[n].material = mat
        
        # bones
        rline()
        rline()
        num_bones = rliteral()
        if num_bones > 0:
            armature_name = 'Armature'
            armature = context.blend_data.armatures.new(armature_name)
            armature_object = context.blend_data.objects.new(armature_name, armature)
            col.objects.link(armature_object)
            modifier = obj.modifiers.new(armature_name, type='ARMATURE')
            modifier.object = armature_object
            obj.parent = armature_object
            
            context.view_layer.objects.active = armature_object
            bpy.ops.object.mode_set(mode = 'EDIT')
            for n in range(num_bones):
                bone_info = rliteral()
                bone_name = bone_info[0]
                bone_parent_name = bone_info[1]
                bone_position = (bone_info[2], bone_info[3], bone_info[4])
                bone_rotation = (bone_info[5], bone_info[6], bone_info[7])
                bone_length = bone_info[8]
                edit_bone = armature.edit_bones.new(bone_name)
                translation_matrix = mathutils.Matrix.Translation(bone_position)
                rotation_matrix = mathutils.Euler(bone_rotation, 'XYZ').to_matrix().to_4x4()
                matrix = translation_matrix @ rotation_matrix
                if bone_parent_name == "":
                    base_bone_correction = mathutils.Matrix.Rotation(- math.pi / 2, 4, 'Z')
                    matrix = base_bone_correction @ matrix
                else:
                    parent = armature.edit_bones.get(bone_parent_name);
                    edit_bone.parent = parent
                    matrix = parent.matrix @ matrix
                edit_bone.length = bone_length
                edit_bone.matrix = matrix
                
                vertex_group = obj.vertex_groups.new(name=bone_name)
                for i in range(num_vertices):
                    vert_info = vertices_info[i]
                    vert_bone = vert_info[6]
                    if vert_bone == n:
                        vertex_group.add((i,), 1., 'ADD')
            bpy.ops.object.mode_set(mode = 'OBJECT')
    
            # animations
            rline()
            rline()
            num_animations = rliteral()
            bpy.ops.object.mode_set(mode = 'POSE')
            for n in range(num_animations):
                animation_info = rliteral()
                animation_name = animation_info
                action = bpy.data.actions.new(animation_name)
                armature_object.animation_data_create()
                armature_object.animation_data.action = action
                for i in range(num_bones):
                    bone_name = rliteral()
                    pose_bone = armature_object.pose.bones.get(bone_name)
                    pose_bone.rotation_mode = 'XZY'
                    num_locations = rliteral()
                    if num_locations > 0:
                        data_path = pose_bone.path_from_id('location')
                        fcurve_location_x = action.fcurves.new(data_path, index=0)
                        fcurve_location_y = action.fcurves.new(data_path, index=1)
                        fcurve_location_z = action.fcurves.new(data_path, index=2)
                        for j in range(num_locations):
                            keyframe_info = rliteral()
                            frame = keyframe_info[0]
                            x = keyframe_info[1]
                            y = keyframe_info[2]
                            z = keyframe_info[3]
                            fcurve_location_x.keyframe_points.insert(frame, x)
                            fcurve_location_y.keyframe_points.insert(frame, y)
                            fcurve_location_z.keyframe_points.insert(frame, z)
                    num_rotations = rliteral()
                    if num_rotations > 0:
                        data_path = pose_bone.path_from_id('rotation_euler')
                        fcurve_rotation_euler_x = action.fcurves.new(data_path, index=0)
                        fcurve_rotation_euler_y = action.fcurves.new(data_path, index=1)
                        fcurve_rotation_euler_z = action.fcurves.new(data_path, index=2)
                        for j in range(num_rotations):
                            keyframe_info = rliteral()
                            frame = keyframe_info[0]
                            x = keyframe_info[1]
                            y = keyframe_info[2]
                            z = keyframe_info[3]
                            fcurve_rotation_euler_x.keyframe_points.insert(frame, x)
                            fcurve_rotation_euler_y.keyframe_points.insert(frame, y)
                            fcurve_rotation_euler_z.keyframe_points.insert(frame, z)
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        # select
        context.view_layer.objects.active = obj
        for object in bpy.context.selected_objects:
            if object is not obj:
                object.select_set(False)
        obj.select_set(True)
        
        # report
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        print("Imported", "in", elapsed_time)

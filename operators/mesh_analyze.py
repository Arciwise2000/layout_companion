import bpy
import bmesh

class MESH_OT_AnalyzeMesh(bpy.types.Operator):
    bl_idname = "mesh.analyze_mesh"
    bl_label = "Clean Mesh"
    bl_description = "Limpia el prop de indeseados vertices"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'
    
    def find_top_parent(self, obj):
        while obj.parent is not None:
            obj = obj.parent
        return obj if obj.type == 'EMPTY' else None
    
    def get_all_meshes(self, context):
        selected_obj = context.active_object
        scene = context.scene

        def collect_meshes_from_empty(obj):
            meshes = []
            def collect(obj):
                if obj.type == 'MESH':
                    meshes.append({
                        'object': obj,
                        'matrix_world': obj.matrix_world.copy(),
                        'name': obj.name,
                        'original_collections': list(obj.users_collection)
                    })
                for child in obj.children:
                    collect(child)
            collect(obj)
            return meshes

        if selected_obj.parent and selected_obj.parent.type == 'EMPTY':
            parent_empty = self.find_top_parent(selected_obj)
            if parent_empty:
                return collect_meshes_from_empty(parent_empty)

        if scene.props_advanced_settings.only_selected_objects:
            selected_meshes = []
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    selected_meshes.append({
                        'object': obj,
                        'matrix_world': obj.matrix_world.copy(),
                        'name': obj.name,
                        'original_collections': list(obj.users_collection)
                    })
            return selected_meshes

        
        elif selected_obj.type == 'MESH' and selected_obj.users_collection:
            target_col = selected_obj.users_collection[0]
            meshes = []
            for obj in target_col.objects:
                if obj.type == 'MESH':
                    meshes.append({
                        'object': obj,
                        'matrix_world': obj.matrix_world.copy(),
                        'name': obj.name,
                        'original_collections': list(obj.users_collection)
                    })
            return meshes
        return [{
            'object': selected_obj,
            'matrix_world': selected_obj.matrix_world.copy(),
            'name': selected_obj.name,
            'original_collections': list(selected_obj.users_collection)
        }]

    def clean_mesh_bmesh(self, obj, remove_doubles=True):
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if remove_doubles:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        
        if hasattr(mesh, "normals_split_custom_set"):
            try:
                mesh.normals_split_custom_set(None)
            except Exception:
                pass

    def tris_to_quads_bmesh(self, obj):
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=40, angle_shape_threshold=40)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    def execute(self, context):
        scene = context.scene
        mesh_data = self.get_all_meshes(context)
        
        if not mesh_data:
            self.report({'WARNING'}, "No mesh data found to clean.")
            return {'CANCELLED'}
        
        parent_empty_name = None
        parent_empty = None
    
        if context.active_object.parent and context.active_object.parent.type == 'EMPTY':
            parent_empty = self.find_top_parent(context.active_object)
            if parent_empty:
                parent_empty_name = parent_empty.name
        
        if scene.props_advanced_settings.remove_empties and parent_empty:
            bpy.ops.object.select_all(action='DESELECT')
            def select_emptys(obj):
                if obj.type == 'EMPTY':
                    obj.select_set(True)
                for child in obj.children:
                    select_emptys(child)
            
            select_emptys(parent_empty)
            if bpy.context.selected_objects:
                bpy.ops.object.delete()
        
        for data in mesh_data:
            obj = data['object']
            obj.matrix_world = data['matrix_world']

            self.clean_mesh_bmesh(obj, remove_doubles=scene.props_advanced_settings.remove_doubles)
            self.tris_to_quads_bmesh(obj)

            # Seleccionar solo el objeto y asegurarse de estar en modo OBJECT
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')

            # Aplicar transformaciones antes de ajustar el origen
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
       
        if scene.props_advanced_settings.mergeObjects and len(mesh_data) > 1:
            bpy.ops.object.select_all(action='DESELECT')
            for data in mesh_data:
                data['object'].select_set(True)
            context.view_layer.objects.active = mesh_data[0]['object']
            bpy.ops.object.join()

            merged_obj = context.active_object
            merged_obj.name = parent_empty_name + "_Merged" if parent_empty_name else "Merged_Object"
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
            final_objects = [merged_obj]
        else:
            final_objects = [data['object'] for data in mesh_data]
                
        if scene.props_advanced_settings.add_in_collection:
            if len(final_objects) == 1:
                uniqueObjName = final_objects[0].name
            else:
                uniqueObjName = "Clean Prop"
                
            if "Clean Prop" not in bpy.data.collections:
                cleanPropName = parent_empty_name if parent_empty_name else uniqueObjName
                clean_prop_col = bpy.data.collections.new(cleanPropName)
                context.scene.collection.children.link(clean_prop_col)
            else:
                clean_prop_col = bpy.data.collections["Clean Prop"]
            
            for obj in final_objects:
                for col in list(obj.users_collection):
                    col.objects.unlink(obj)
                clean_prop_col.objects.link(obj)
        
        return {'FINISHED'}
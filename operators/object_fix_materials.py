import bpy

class MESH_OT_FixMaterials(bpy.types.Operator):
    bl_idname = "mesh.fix_materials"
    bl_label = "Fix Materials"
    bl_description = "Limpia los materiales para su correcta visualizacion en CYCLES"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def find_principled_node(self, socket):
        if not socket.is_linked:
            return None
        
        from_node = socket.links[0].from_node
        
        if from_node.type == 'BSDF_PRINCIPLED':
            return from_node
        elif from_node.type == 'MIX_SHADER':
            for input_socket in from_node.inputs[:2]:
                result = self.find_principled_node(input_socket)
                if result:
                    return result
        else:
            for input_socket in from_node.inputs:
                result = self.find_principled_node(input_socket)
                if result:
                    return result
        return None

    def execute(self, context):
        select_objs = context.selected_objects

        for obj in select_objs:
            if obj.type != "MESH":
                continue

            for mat in obj.data.materials:
                if mat and mat.use_nodes:
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links
                    output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

                    if not output_node:
                        continue

                    surface_socket = output_node.inputs.get('Surface')

                    if not surface_socket or not surface_socket.is_linked:
                        continue

                    from_node = surface_socket.links[0].from_node

                    if from_node.type in ['EMISSION', 'TEX_IMAGE']:
                        principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
                        principled_node.location = from_node.location.x - 200, from_node.location.y

                        links.new(principled_node.outputs['BSDF'], surface_socket)

                        if from_node.type == 'EMISSION':
                            emission_input = from_node.inputs['Color']
                            if emission_input.is_linked:
                                image_node = emission_input.links[0].from_node
                                if image_node.type == 'TEX_IMAGE':
                                    links.new(image_node.outputs['Color'], principled_node.inputs['Base Color'])
                            else:
                                principled_node.inputs['Base Color'].default_value = emission_input.default_value

                        elif from_node.type == 'TEX_IMAGE':
                            links.new(from_node.outputs['Color'], principled_node.inputs['Base Color'])
                            
                    principled = self.find_principled_node(surface_socket)
                    if principled:
                        principled.inputs['Emission Strength'].default_value = 0.0
                    else:
                        # Buscar el primer nodo de textura en el árbol de nodos
                        image_node = next((n for n in nodes if n.type == 'TEX_IMAGE'), None)
                        
                        if image_node:
                            principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
                            principled_node.location = image_node.location.x - 200, image_node.location.y

                            links.new(image_node.outputs['Color'], principled_node.inputs['Base Color'])
                            
                            links.new(principled_node.outputs['BSDF'], surface_socket)


        return {'FINISHED'}
    
_emission_mode_enabled = False

class MESH_OT_EmissionView(bpy.types.Operator):
    bl_idname = "mesh.emission_view"
    bl_label = ""
    bl_description = "Alterna entre shading COMBINED y EMISSION"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global _emission_mode_enabled
        area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if not area:
            return {'CANCELLED'}

        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
                _emission_mode_enabled = not _emission_mode_enabled
                space.shading.render_pass = 'EMISSION' if _emission_mode_enabled else 'COMBINED'
                break

        return {'FINISHED'}

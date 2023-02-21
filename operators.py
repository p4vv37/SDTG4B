import pathlib
import socket
import threading
import time

import requests
import math
import mathutils
import os
import bpy
from bpy.types import Operator


class SDProcessor(threading.Thread):
    waiting_for_render = False
    waiting_for_refresh = False
    camera_location = (0, 0, 0)
    stop = False

    def __init__(self,
                 data, api_url, resolution_x, resolution_y, camera_r, camera_z, wm, views_num, camera):
        self.data = data
        self.api_url = api_url
        self.resolution_x = resolution_x
        self.resolution_y = resolution_y
        self.camera_r = camera_r
        self.camera_z = camera_z
        self.views_num = views_num
        self.camera = camera
        self.iteration = 0
        threading.Thread.__init__(self)

    def finish_texture(self):
        data = self.data.copy()
        response = requests.get(self.api_url + "/finish_texture", json=data)
        print(response.status_code, response.text)

    def depth2img(self, **kwargs):
        data = self.data.copy()
        data.update(kwargs)
        try:
            requests.get(self.api_url + "/depth2img_step", json=data, timeout=1)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout):
            pass

        while True:
            try:
                requests.get(self.api_url + "/status", json={}, timeout=1)
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ReadTimeout):
                continue
            break

    def render_view(self, angle, z_offset=2, radius=7):
        print(F"Rendering: {angle} in thread.")

        angle_radians = 2 * math.pi * angle / 360

        # Randomly place the camera on a circle around the object at the same height as the main camera
        new_camera_pos = mathutils.Vector((self.camera_r * math.cos(angle_radians),
                                           radius * math.sin(angle_radians),
                                           self.camera_z))
        self.camera_location = new_camera_pos

        # Render UVs and Depth
        self.waiting_for_render = True
        while self.waiting_for_render:
            time.sleep(1)
        self.iteration += 1

    def run(self):

        number_of_renders = self.views_num
        for num in range(number_of_renders):
            angle = 360 * num / number_of_renders
            self.render_view(angle)
            if self.stop:
                return
            self.depth2img()
            bpy.context.window_manager.progress_update(70 * num // number_of_renders)
            if self.stop:
                return
        # top part problem
        self.render_view(0, z_offset=3, radius=3)
        if self.stop:
            return
        self.depth2img(strength=0.5)
        bpy.context.window_manager.progress_update(80)

        self.render_view(0)
        if self.stop:
            return
        self.depth2img(strength=0.5)
        bpy.context.window_manager.progress_update(90)

        self.finish_texture()

        bpy.context.window_manager.progress_update(100)
        bpy.context.window_manager.progress_end()
        self.waiting_for_refresh = True


def create_material(txt_path):
    output_image = bpy.data.images.new(str(txt_path), width=768, height=768)
    output_image.file_format = 'PNG'
    output_image.filepath = str(txt_path)
    output_image.save()

    mat = bpy.data.materials.get("SDResultMaterial")
    if mat is None:
        mat = bpy.data.materials.new(name="SDResultMaterial")
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get('Principled BSDF')

    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = output_image
    mat.node_tree.links.new(tex_node.outputs[0], principled.inputs[0])

    uv_node = mat.node_tree.nodes.new("ShaderNodeTexCoord")
    aov_out_node = mat.node_tree.nodes.new("ShaderNodeOutputAOV")
    aov_out_node.name = "UV"
    mat.node_tree.links.new(uv_node.outputs[2], aov_out_node.inputs[0])
    return mat


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

PROCESS_CACHE = None


class WM_OT_RunSD(Operator):
    bl_label = "Run SD server"
    bl_idname = "wm.start_sd_server"

    def execute(self, context):
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((sd_tool.host, sd_tool.port))
        if result == 0:
            self.report({"INFO"}, "Port is already taken or the server is already running.")
            return {'FINISHED'}
        import subprocess

        if "SDTG4B_CONDA" not in str(subprocess.check_output("conda info --envs ")):
            self.report({"ERROR"}, F"Conda environment SDTG4B_CONDA not found in the system. "
                                   F"Please make sure, that proper environment exists.")
            return {'FINISHED'}
        global PROCESS_CACHE
        script_path = os.path.dirname(__file__) + os.sep + "start_sd_server.py"
        PROCESS_CACHE = subprocess.Popen(["conda", "run", "-n", "SDTG4B_CONDA", "python", script_path])
        return {'FINISHED'}


class WM_OT_PreviewCameraPath(Operator):
    bl_label = "Generate camera path preview"
    bl_idname = "wm.preview_camera"

    def execute(self, context):
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        if sd_tool.out_txt == os.sep + "txt.png" or not sd_tool.out_txt:
            txt_path = str(self.result_path / "txt.png")
        else:
            txt_path = self.sd_tool.out_txt
        return {'FINISHED'}


class WM_OT_CreateMaterial(Operator):
    bl_label = "Create material, that will be used by the tool"
    bl_idname = "wm.create_sd_material"

    def execute(self, context):
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        if sd_tool.out_txt == os.sep + "txt.png" or not sd_tool.out_txt:
            txt_path = str(self.result_path / "txt.png")
        else:
            txt_path = self.sd_tool.out_txt
        create_material(txt_path)

        return {'FINISHED'}


class WM_OT_GenerateTxt(Operator):
    bl_label = "Generate textures"
    bl_idname = "wm.generate_txt"
    output_img_path = ""
    api_url = ""
    sd_tool = None
    out_path = pathlib.Path()
    tmp_path = pathlib.Path()
    result_path = pathlib.Path()
    txt_path = pathlib.Path()
    wm = None
    t = None
    progress = 0.0
    _timer = None
    t_cache = list()

    def generate_data(self):
        frame_code = "{0:0>4}".format(bpy.context.scene.frame_current)

        return {
            "prompt": self.sd_tool.prompt,
            "n_prompt": self.sd_tool.negative_prompt,
            "depth": str(self.tmp_path / F"depth{frame_code}.bmp"),
            "uv": str(self.tmp_path / F"uv{frame_code}.exr"),
            "out_txt": self.txt_path,
            "render": str(self.tmp_path / F"Image{frame_code}.png"),
            "alpha": str(self.tmp_path / F"alpha{frame_code}.png"),
            "diffuse": str(self.tmp_path / F"diffuse{frame_code}.bmp"),
            "depth_based_mixing": self.sd_tool.depth_based_blending,
            "steps": self.sd_tool.num_inference_steps,
            "guidance_scale": self.sd_tool.guidance_scale,
            "seed": self.sd_tool.seed
        }

    def setup_composition_nodes_and_material(self):
        print("Preparing the scene..")
        # Materials, textures...
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree
        for node in tree.nodes:
            if node.label == "Output":
                node.base_path = str(pathlib.Path(self.result_path))

        bpy.context.window_manager.progress_update(33)

        # Create/use material
        if self.sd_tool.clear_txt and os.path.exists(self.txt_path):
            os.remove(self.txt_path)
        mat = create_material(self.txt_path)

        if self.sd_tool.target.data.materials:
            self.sd_tool.target.data.materials[0] = mat
        else:
            # no slots
            self.sd_tool.target.data.materials.append(mat)

        # Render and composition
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree
        for node in tree.nodes:
            tree.nodes.remove(node)

        bpy.data.scenes["Scene"].view_layers["ViewLayer"].use_pass_diffuse_color = True
        bpy.data.scenes["Scene"].view_layers["ViewLayer"].use_pass_combined = True
        bpy.data.scenes["Scene"].view_layers["ViewLayer"].use_pass_z = True
        try:
            bpy.data.scenes["Scene"].view_layers["ViewLayer"].uv = False
        except Exception:
            pass
        bpy.ops.scene.view_layer_add_aov()
        bpy.data.scenes["Scene"].view_layers["ViewLayer"].active_aov.name = "UV"

        bpy.data.scenes["Scene"].render.film_transparent = True
        bpy.data.scenes["Scene"].render.engine = 'BLENDER_EEVEE'

        render_layers = tree.nodes.new('CompositorNodeRLayers')

        # depth
        depth_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
        depth_file_output.label = 'Depth Output'
        depth_file_output.base_path = str(self.tmp_path)
        depth_file_output.file_slots[0].path = "depth"
        depth_file_output.file_slots[0].use_node_format = True
        depth_file_output.format.file_format = "BMP"

        normalize_node = tree.nodes.new(type="CompositorNodeNormalize")

        tree.links.new(render_layers.outputs['Depth'], normalize_node.inputs[0])
        tree.links.new(normalize_node.outputs['Value'], depth_file_output.inputs[0])

        bpy.context.window_manager.progress_update(70)

        # uv
        uv_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
        uv_file_output.label = 'UV Output'
        uv_file_output.base_path = str(self.tmp_path)
        uv_file_output.file_slots[0].path = "uv"
        uv_file_output.file_slots[0].use_node_format = True
        uv_file_output.format.file_format = "OPEN_EXR"
        uv_file_output.format.color_depth = '32'
        tree.links.new(render_layers.outputs['UV'], uv_file_output.inputs[0])

        bpy.context.window_manager.progress_update(80)

        # alpha
        alpha_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
        alpha_file_output.label = 'Alpha Output'
        alpha_file_output.base_path = str(self.tmp_path)
        alpha_file_output.file_slots[0].path = "alpha"
        alpha_file_output.file_slots[0].use_node_format = True
        alpha_file_output.format.file_format = "PNG"
        alpha_file_output.format.color_mode = "BW"
        tree.links.new(render_layers.outputs['Alpha'], alpha_file_output.inputs[0])

        bpy.context.window_manager.progress_update(90)

        # diffuse
        diffuse_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
        diffuse_file_output.label = 'Diffuse Output'
        diffuse_file_output.base_path = str(self.tmp_path)
        diffuse_file_output.file_slots[0].path = "diffuse"
        diffuse_file_output.file_slots[0].use_node_format = True
        diffuse_file_output.format.file_format = "BMP"

        luma_key_node = tree.nodes.new("CompositorNodeLumaMatte")
        luma_key_node.limit_max = 0.01
        luma_key_node.limit_min = 0.00
        tree.links.new(render_layers.outputs['DiffCol'], luma_key_node.inputs[0])

        mix_node = tree.nodes.new("CompositorNodeMixRGB")
        tree.links.new(luma_key_node.outputs['Matte'], mix_node.inputs[0])
        tree.links.new(render_layers.outputs['Image'], mix_node.inputs[1])
        tree.links.new(render_layers.outputs['DiffCol'], mix_node.inputs[2])

        tree.links.new(mix_node.outputs['Image'], diffuse_file_output.inputs[0])

        # Image

        # alpha
        image_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
        image_file_output.label = 'Alpha Output'
        image_file_output.base_path = str(self.tmp_path)
        image_file_output.file_slots[0].path = "Image"
        image_file_output.file_slots[0].use_node_format = True
        image_file_output.format.file_format = "PNG"
        tree.links.new(render_layers.outputs['Image'], image_file_output.inputs[0])

        bpy.context.window_manager.progress_update(99)

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER' and self.t is not None:
            min_value = 100 * (max(self.t.iteration - 1, 0) / (self.t.views_num + 2))
            max_value = 100 * (self.t.iteration / (self.t.views_num + 2))
            delta = max_value - min_value
            self.progress += 0.05 * (delta - self.progress)
            bpy.context.window_manager.progress_update(min_value + + self.progress)

        if self.t is not None and self.t.is_alive():
            if self.t.waiting_for_render:
                print("RENDER!")
                # Reload textures:
                for img in bpy.data.images:
                    img.reload()

                # Basic parameters
                scene = bpy.data.scenes['Scene']
                render = scene.render

                # Resolution change
                render.resolution_x = self.sd_tool.resolution_x
                render.resolution_y = self.sd_tool.resolution_y

                bpy.context.scene.camera.location = self.t.camera_location

                bpy.ops.render.render()
                self.t.waiting_for_render = False
                self.progress = 0.0
            if self.t.waiting_for_refresh:
                for img in bpy.data.images:
                    img.reload()
                self.t.waiting_for_refresh = False
            return {'PASS_THROUGH'}
        print("END")
        time.sleep(1)
        for img in bpy.data.images:
            img.reload()
        return {'FINISHED'}

    def cancel(self, context):
        self.t.stop = True
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

    def invoke(self, context, event):
        print("Invoked")
        self.progress = 0.0
        scene = context.scene
        self.sd_tool = scene.sd_txt_tool
        bpy.context.window_manager = bpy.context.window_manager

        for value_name in ("prompt", "target", "out_dir"):
            if not getattr(self.sd_tool, value_name):
                self.report({"ERROR"}, F"{value_name} value cannot be empty")
                return {'CANCELLED'}

        if self.sd_tool.out_dir and self.sd_tool.out_dir != "cwd":
            self.out_path = pathlib.Path(self.sd_tool.out_dir)
        else:
            self.out_path = pathlib.Path(bpy.path.abspath("//"))

        if not self.out_path.exists() or not self.out_path.is_dir():
            self.report({"ERROR"}, F"Output directory '{self.out_path}' is not correct")
            return {'CANCELLED'}

        self.tmp_path = self.out_path / "tmp"
        self.result_path = self.out_path / "result"
        self.tmp_path.mkdir(exist_ok=True)
        self.result_path.mkdir(exist_ok=True)

        if self.sd_tool.out_txt == "cwd" + os.sep + "txt.png" or not self.sd_tool.out_txt:
            self.txt_path = str(self.result_path / "txt.png")
        else:
            self.txt_path = self.sd_tool.out_txt

        self.api_url = F"http://{self.sd_tool.host}:{self.sd_tool.port}"
        try:
            requests.get(self.api_url + "/status", json={}, timeout=1)
        except (ConnectionError, requests.exceptions.ConnectTimeout, requests.exceptions.Timeout):
            self.report({"ERROR"},
                        F"""Port {self.sd_tool.port} of host {self.sd_tool.host} is not opened.
Start the Stable Diffusion server by:
- Executing the file start_sd_server.py
- SD Server Settings >> Run SD Server
Tf the server is running, make sure, that port and host of SD server are correct.""")
            return {'CANCELLED'}
        except requests.exceptions.ConnectTimeout:
            pass

        bpy.context.window_manager.progress_begin(0, 100)
        bpy.context.window_manager.progress_update(0)

        self.setup_composition_nodes_and_material()

        bpy.context.window_manager.progress_update(0)

        bpy.ops.object.camera_add(enter_editmode=False)
        camera = bpy.context.object
        bpy.context.scene.camera = camera

        # Add a new track to constraint and set it to track your object
        track_to = bpy.context.object.constraints.new('TRACK_TO')
        track_to.target = self.sd_tool.target
        track_to.track_axis = 'TRACK_NEGATIVE_Z'
        track_to.up_axis = 'UP_Y'

        self.t_cache.append(self.t)
        self.t = SDProcessor(data=self.generate_data(),
                             api_url=self.api_url,
                             resolution_x=self.sd_tool.resolution_x, resolution_y=self.sd_tool.resolution_y,
                             camera_r=self.sd_tool.camera_r, camera_z=self.sd_tool.camera_z,
                             wm=bpy.context.window_manager,
                             views_num=self.sd_tool.views_num,
                             camera=camera)

        self.t.start()
        self._timer = bpy.context.window_manager.event_timer_add(1, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

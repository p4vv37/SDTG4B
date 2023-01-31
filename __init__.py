import os
import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       )

from .operators import (WM_OT_RunSD,
                        WM_OT_GenerateTxt,
                        WM_OT_PreviewCameraPath
                        )

bl_info = {
    "name": "Stable Diffusion textures generator",
    "description": "",
    "author": "Pawel Kowalski",
    "version": (0, 0, 1),
    "blender": (2, 80, 0),
    "location": "3D View > Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Material"
}


class SDProperties(PropertyGroup):
    prompt: StringProperty(
        name="Prompt",
        description="Description of desired image",
        default="An oil painting of a pirate treasure chest, gold, coins, highly detailed, trending on artstation, "
                "concept art, Professional, gold coins on ground, wooden box with wooden cover",
        maxlen=256,
        subtype='NONE'
    )

    negative_prompt: StringProperty(
        name="Negative prompt",
        description="Description of how image should not look like",
        default="blue topping, dark, shadows, bright spots, glossy, only gold",
        maxlen=256,
        subtype='NONE'
    )

    out_dir: StringProperty(
        name="Output directory",
        description="Directory for output and temporary files.",
        default="cwd",
        maxlen=256,
        subtype='DIR_PATH'
    )

    out_txt: StringProperty(
        name="Output directory",
        description="Directory for output and temporary files.",
        default="cwd" + os.sep + "txt.png",
        maxlen=256,
        subtype='DIR_PATH'
    )

    host: StringProperty(
        name="SD server host address",
        description="Stable Diffusion server address",
        default="127.0.0.1",
        maxlen=256,
        subtype='NONE'
    )

    num_inference_steps: IntProperty(
        name="Number of interference steps",
        description="A number of denoising steps",
        default=30,
        min=1,
        max=100
    )

    guidance_scale: FloatProperty(
        name="Guidance scale",
        description="Scale for classifier-free guidance",
        default=7.5,
        min=1.0,
        max=20.0
    )

    seed: IntProperty(
        name="Seed",
        description="Random seed",
        default=1234567,
        min=0
    )

    views_num: IntProperty(
        name="Number of views",
        description="Number of views that will be rendered around the object for texture generation",
        default=4,
        min=0,
        max=8
    )

    camera_r: FloatProperty(
        name="Camera radius",
        description="Radius of camera path",
        default=6.0,
        min=1.0,
        max=20.0
    )

    camera_z: FloatProperty(
        name="Camera Z position",
        description="Z position of camera path",
        default=2,
        min=1.0,
        max=20.0
    )

    port: IntProperty(
        name="Server port",
        description="Port of stable diffusion server",
        default=5000,
        min=0
    )

    target: PointerProperty(
        name="Server port",
        description="Port of stable diffusion server",
        type=bpy.types.Object
    )

    depth_based_blending: BoolProperty(
        name="Depth-based blending",
        description="Enable/disable depth-based renders blending for texture",
        default=True
    )

    clear_txt: BoolProperty(
        name="Start with empty texture",
        description="If enabled, the output texture will be cleared before generation.\n"
                    "If disabled, the output texture will be used as a starting point for generation\n"
                    "This might improve control over the result and improve quality of the result.",
        default=True
    )

    resolution_x: IntProperty(
        name="Resolution X",
        description="Resolution X",
        default=768,
        min=0
    )

    resolution_y: IntProperty(
        name="Resolution Y",
        description="Resolution X",
        default=512,
        min=0
    )

    # my_enum: EnumProperty(
    #     name="Dropdown:",
    #     description="Apply Data to attribute.",
    #     items=[('OP1', "Option 1", ""),
    #            ('OP2', "Option 2", ""),
    #            ('OP3', "Option 3", ""),
    #            ]
    # )


# ------------------------------------------------------------------------
#    Menus
# ------------------------------------------------------------------------


class OBJECT_MT_CustomMenu(Menu):
    bl_label = "Select"
    bl_idname = "OBJECT_MT_custom_menu"

    def draw(self, context):
        layout = self.layout

        # Built-in operators
        layout.operator("object.select_all", text="Select/Deselect All").action = 'TOGGLE'
        layout.operator("object.select_all", text="Inverse").action = 'INVERT'
        layout.operator("object.select_random", text="Random")


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------


class OBJECT_PT_MainSDPanel(Panel):
    bl_label = "Stable Diffusion Texture Generator"
    bl_idname = "OBJECT_PT_main_sd_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"
    bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        layout.label(text="SD generation settings")
        layout.prop(sd_tool, "prompt")
        layout.prop(sd_tool, "negative_prompt")
        layout.prop(sd_tool, "target")
        layout.prop(sd_tool, "out_dir")
        layout.prop(sd_tool, "out_txt")
        layout.prop(sd_tool, "clear_txt")


class OBJECT_PT_SDPanel(Panel):
    bl_label = "Stable Diffusion settings"
    bl_idname = "OBJECT_PT_sd_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"
    bl_context = "objectmode"
    bl_parent_id = "OBJECT_PT_main_sd_panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        layout.prop(sd_tool, "depth_based_blending")
        layout.prop(sd_tool, "num_inference_steps")
        layout.prop(sd_tool, "guidance_scale")
        layout.prop(sd_tool, "seed")
        layout.prop(sd_tool, "resolution_x")
        layout.prop(sd_tool, "resolution_y")


class OBJECT_PT_ScenePanel(Panel):
    bl_label = "Scene settings"
    bl_idname = "OBJECT_PT_scene_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"
    bl_context = "objectmode"
    bl_parent_id = "OBJECT_PT_main_sd_panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        layout.prop(sd_tool, "views_num")
        layout.prop(sd_tool, "camera_r")
        layout.prop(sd_tool, "camera_z")
        # layout.operator("wm.preview_camera")


class OBJECT_PT_ServerPanel(Panel):
    bl_label = "SD server settings"
    bl_idname = "OBJECT_PT_server_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"
    bl_context = "objectmode"
    bl_parent_id = "OBJECT_PT_main_sd_panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        layout.prop(sd_tool, "host")
        layout.prop(sd_tool, "port")
        layout.operator("wm.start_sd_server")


class OBJECT_PT_ActionsPanel(Panel):
    bl_label = "Execute"
    bl_idname = "OBJECT_PT_actions_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"
    bl_context = "objectmode"
    bl_parent_id = "OBJECT_PT_main_sd_panel"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        sd_tool = scene.sd_txt_tool

        layout.operator("wm.generate_txt")
# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    SDProperties,
    WM_OT_RunSD,
    WM_OT_GenerateTxt,
    WM_OT_PreviewCameraPath,
    OBJECT_PT_MainSDPanel,
    OBJECT_PT_SDPanel,
    OBJECT_PT_ScenePanel,
    OBJECT_PT_ServerPanel,
    OBJECT_PT_ActionsPanel
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.sd_txt_tool = PointerProperty(type=SDProperties)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.sd_txt_tool


if __name__ == "__main__":
    register()

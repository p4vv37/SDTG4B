# SDTG4B
Stable Diffusion Texture Generator For Blender

![obraz](https://user-images.githubusercontent.com/3722204/215628215-339e9609-86ac-40f7-8478-77077ffeec4e.png)

https://user-images.githubusercontent.com/3722204/214519268-2d9e45e6-711e-45fd-b461-fff06c17f1d1.mp4

https://user-images.githubusercontent.com/3722204/213944732-2a86cb32-83b0-43c3-b83b-8fa765138b24.mp4

https://user-images.githubusercontent.com/3722204/215635067-d8b07c4f-06b8-4388-8777-6bb3262934c2.mp4

# How to install
- Download and install the zip file of the current release from: https://github.com/p4vv37/SDTG4B/releases/tag/release
![obraz](https://user-images.githubusercontent.com/3722204/215626359-36699423-6668-4382-b617-48a0df0e29e1.png)

- Create a new Conda environment described in [environment.yml](https://github.com/p4vv37/SDTG4B/blob/main/environment.yml) file by using the command:
    
    conda env update --file environment.yml  --prune      
   

# How to generate texture
 
- Run the [start_sd_server.py](https://github.com/p4vv37/SDTG4B/blob/main/start_sd_server.py) file in conda environment with required packages or use the SD server settings > Run SD server button from plugin UI.

- The plugin UI should be visible in the 3D Viewport during object mode 

- Set a value for the Target object. **Target object need to have correct UVs**

- Print the Generate textures button of the plugin UI

- Creating a simple texture and unchecking the Start with empty texture" checkbox greatly influences a quality of the result.

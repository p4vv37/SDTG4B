# SDTG4B
Stable Diffusion Texture Generator For Blender

![obraz](https://user-images.githubusercontent.com/3722204/215626232-3c5ae6e2-8f06-4ae8-a03c-a0b400254873.png)

https://user-images.githubusercontent.com/3722204/214519268-2d9e45e6-711e-45fd-b461-fff06c17f1d1.mp4

https://user-images.githubusercontent.com/3722204/213944732-2a86cb32-83b0-43c3-b83b-8fa765138b24.mp4


# How to install
- Download and install the zip file of the current release from: https://github.com/p4vv37/SDTG4B/releases/tag/release
![obraz](https://user-images.githubusercontent.com/3722204/215626359-36699423-6668-4382-b617-48a0df0e29e1.png)

- Create a new Conda environment described in [environment.yml](https://github.com/p4vv37/SDTG4B/blob/main/environment.yml) file by using the command:
    
    conda env update --file environment.yml  --prune      
   

# How to generate texture
 
- Run the [start_sd_server.py](https://github.com/p4vv37/SDTG4B/blob/main/start_sd_server.py) file in conda environment with required packages or use the SD server settings > Run SD server button from plugin UI.

- Set a value for the Target object. **Target object need to have correct UVs**

- Print the Generate textures button of the plugin UI

- Creating a simple texture and unchecking the Start with empty texture" checkbox greatly influences a quality of the result.

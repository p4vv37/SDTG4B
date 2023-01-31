import pathlib
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import torch
from diffusers import StableDiffusionDepth2ImgPipeline
from PIL import Image, ImageChops
import numpy as np
import cv2
import os


def finish_texture(out_img_arr, partial=False):
    for x in range(out_img_arr.shape[0]):
        for y in range(out_img_arr.shape[1]):
            color = out_img_arr[x][y]
            if sum(color) < 0.00001:
                number_of_colors = 0
                out_color = np.array([0, 0, 0])
                for x1, y1 in [[x, y - 1], [x, y + 1]]:
                    if x1 >= out_img_arr.shape[0] or y1 >= out_img_arr.shape[1]:
                        continue
                    c = out_img_arr[x1][y1]
                    if sum(c) > 0.00001:
                        out_color += c
                        number_of_colors += 1
                if number_of_colors == 0 or (partial and number_of_colors < 2):
                    continue
                out_color = out_color / float(number_of_colors)
                out_img_arr[x, y] = out_color

    for x in range(out_img_arr.shape[0]):
        for y in range(out_img_arr.shape[1]):
            color = out_img_arr[x][y]
            if sum(color) < 0.00001:
                number_of_colors = 0
                out_color = np.array([0, 0, 0])
                for x1, y1 in [[x - 1, y], [x + 1, y]]:
                    if x1 >= out_img_arr.shape[0] or y1 >= out_img_arr.shape[1]:
                        continue
                    c = out_img_arr[x1][y1]
                    if sum(c) > 0.00001:
                        out_color += c
                        number_of_colors += 1
                if number_of_colors == 0 or (partial and number_of_colors < 2):
                    continue
                out_color = out_color / float(number_of_colors)
                out_img_arr[x, y] = out_color
    return out_img_arr


class Handler(BaseHTTPRequestHandler):
    depth2img_pipe = StableDiffusionDepth2ImgPipeline.from_pretrained(
        "stabilityai/stable-diffusion-2-depth",
        torch_dtype=torch.float16,
    ).to("cuda")

    # noinspection PyPep8Naming
    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header('python 3 ', 'text/html')
            self.end_headers()
            return

        length = int(self.headers.get('content-length'))
        field_data = self.rfile.read(length)
        data = json.loads(str(field_data, "UTF-8"))

        prompt = data.get("prompt")
        n_prompt = data.get("n_prompt", "")

        num_inference_steps = data.get("steps")
        depth_path = data.get("depth")
        src_path = data.get("render")
        uv_path = data.get("uv")
        alpha_path = data.get("alpha")
        out_txt_path = data.get("out_txt")
        diffuse_path = data.get("diffuse")
        strength = float(data.get("strength", 0.8))
        depth_based_mixing = int(data.get("depth_based_mixing", False))

        seed = data.get("seed", 1024)
        generator = torch.Generator(device="cuda").manual_seed(seed)

        if prompt is None or out_txt_path is None:
            self.send_response(400)
            self.send_header('Incorrect payload', 'text/html')
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('python 3 ', 'text/html')
        self.end_headers()

        if self.path == "/depth2img_step":
            init_img = Image.open(src_path)
            original_alpha_img = Image.open(alpha_path).convert("RGB")
            diffuse_img = Image.open(diffuse_path)
            gray = Image.new('RGB', diffuse_img.size, (128, 128, 128))
            diffuse_img = ImageChops.blend(diffuse_img, gray, 0.5 * strength)
            diffuse_img = ImageChops.multiply(diffuse_img, original_alpha_img)
            # diffuse_img.save(r"C:\git\NeuralNetworksSketchbook\sd_texturing\tmp\test.png")
            depth_arr = np.array(Image.open(depth_path).convert("L"))
            depth_arr *= 1000
            depth_arr += 1000
            depth_arr = np.expand_dims(depth_arr, axis=0)
            depth_arr = torch.from_numpy(depth_arr)

            img = self.depth2img_pipe(prompt=prompt, image=diffuse_img, depth_map=depth_arr, negative_prompt=n_prompt,
                                      guidance_scale=9, strength=0.8, generator=generator,
                                      num_inference_steps=num_inference_steps, num_images_per_prompt=1).images[0]
            img.save(pathlib.Path(src_path).parent / "prev.png")

            os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"

            scaled_img_size = [x * 2 for x in init_img.size]

            # Scale for UV interpolation
            img = np.array(img.resize(scaled_img_size, Image.Resampling.BICUBIC))
            depth_arr = np.array(Image.open(depth_path).resize(scaled_img_size, Image.Resampling.BICUBIC))
            uv_img = cv2.imread(uv_path, cv2.IMREAD_UNCHANGED)
            uv_img = cv2.cvtColor(uv_img, cv2.COLOR_BGR2RGB)
            uv_img = cv2.resize(uv_img, scaled_img_size, interpolation=cv2.INTER_CUBIC)
            alpha_img = Image.open(alpha_path).resize(scaled_img_size, Image.Resampling.BICUBIC)

            # diffuse_img = Image.open(diffuse_path)

            uv_img_arr = np.asarray(uv_img)
            uv_img_arr = np.clip(uv_img_arr, 0, 1.0)
            img_arr = np.asarray(img)

            out_img = Image.open(out_txt_path)
            out_img_arr = np.array(out_img)
            wip_out_img_arr = out_img_arr.copy()
            src_alpha_arr = np.array(alpha_img)

            for x in range(uv_img_arr.shape[0]):
                for y in range(uv_img_arr.shape[1]):
                    u, v, w = uv_img_arr[x][y]
                    a = src_alpha_arr[x][y]
                    try:
                        if a > 244 and sum([u, v, w]) > 0.00000001:
                            u2 = int(out_img_arr.shape[1] - 1) - int(out_img_arr.shape[1] * v) - 1
                            v2 = int(out_img_arr.shape[0] * u) - 1

                            if depth_based_mixing and sum(out_img_arr[u2, v2]) > 0:
                                depth = (np.clip(depth_arr[x][y][0] / 255, 0, 0.5) * 2) ** 2
                                wip_out_img_arr[u2, v2] = img_arr[x][y] * (1 - depth) + out_img_arr[u2, v2] * depth
                            else:
                                wip_out_img_arr[u2, v2] = img_arr[x][y]
                    except Exception as e:
                        pass
            for x in range(out_img_arr.shape[0]):
                for y in range(out_img_arr.shape[1]):
                    if depth_based_mixing:
                        out_img_arr[x, y] = wip_out_img_arr[x][y]
                    elif sum(out_img_arr[x, y]) == 0:
                        out_img_arr[x, y] = wip_out_img_arr[x][y]

            out_img_arr = finish_texture(out_img_arr, partial=True)
            out = Image.fromarray(out_img_arr.astype('uint8'), 'RGB')
            out.save(out_txt_path)

        if self.path == "/finish_texture":
            out_img = Image.open(out_txt_path)
            out_img_arr = np.array(out_img)
            out_img_arr = finish_texture(out_img_arr)
            out = Image.fromarray(out_img_arr.astype('uint8'), 'RGB')
            out.save(out_txt_path)

        message = F"Request {self.path} processed"
        print(message)
        self.wfile.write(bytes(message, "utf8"))


def start_server(port):
    with HTTPServer(('127.0.0.1', port), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    start_server(5000)

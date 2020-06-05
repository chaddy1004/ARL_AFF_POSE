import numpy as np
import shutil
import glob
import os

# =================== new directory ========================
folder_to_save = '/data/Akeaveny/Datasets/test4/combined1/'

# =================== load from ========================
images_path1 = '/data/Akeaveny/Datasets/test4/cup_01/Kinetic/0000??'
images_path2 = '/data/Akeaveny/Datasets/test4/cup_01/ZED/0000??'
images_path3 = '/data/Akeaveny/Datasets/test4/knife_01/Kinetic/0000??'
images_path4 = '/data/Akeaveny/Datasets/test4/knife_01/ZED/0000??'
images_path5 = '/data/Akeaveny/Datasets/test4/missing/Kinetic/0000??'

# =================== images ext ========================
image_ext1 = '.json'
image_ext11 = '.right.json'
image_ext12 = '.left.json'

image_ext2 = '.cs.png'
image_ext3 = '.right.cs.png'
image_ext4 = '.left.cs.png'

image_ext5 = '.depth.16.png'
image_ext6 = '.right.depth.16.png'
image_ext7 = '.left.depth.16.png'

image_ext8 = '.png'
image_ext9 = '.right.png'
image_ext10 = '.left.png'

# image_exts = [image_ext1, image_ext2, image_ext3, image_ext4, image_ext5, image_ext6, image_ext7, image_ext8, image_ext9, image_ext10]

# image_paths = [images_path1, images_path3, images_path5]
# image_exts = [image_ext1, image_ext2, image_ext5, image_ext8]
# offset = 0
# image_paths = [images_path2, images_path4]
# image_exts = [image_ext11, image_ext3, image_ext6, image_ext9]
# offset = 300
image_paths = [images_path2, images_path4]
image_exts = [image_ext12, image_ext4, image_ext7, image_ext10]
offset = 500

# =================== new directory ========================
for image_path in image_paths:
    files = None
    for image_ext in image_exts:
        file_path = image_path + image_ext
        print("File path: ", file_path)
        files = sorted(glob.glob(file_path))
        print("Loaded files: ", len(files))

        for idx, file in enumerate(files):
            old_file_name = file

            # image_num = offset + idx
            count = 100000 + offset + idx
            image_num = str(count)[1:]

            if image_ext == ".json":
                new_file_name = folder_to_save + np.str(image_num) + '.json'
            elif image_ext == ".right.json":
                new_file_name = folder_to_save + np.str(image_num) + '.json'
            if image_ext == ".left.json":
                new_file_name = folder_to_save + np.str(image_num) + '.json'

            elif image_ext == ".png":
                new_file_name = folder_to_save + np.str(image_num) + '_rgb.png'
            elif image_ext == ".right.png":
                new_file_name = folder_to_save + np.str(image_num) + '_rgb.png'
            elif image_ext == ".left.png":
                new_file_name = folder_to_save + np.str(image_num) + '_rgb.png'

            elif image_ext == ".depth.16.png":
                new_file_name = folder_to_save + np.str(image_num) + '_depth.png'
            elif image_ext == ".right.depth.16.png":
                new_file_name = folder_to_save + np.str(image_num) + '_depth.png'
            elif image_ext == ".left.depth.16.png":
                new_file_name = folder_to_save + np.str(image_num) + '_depth.png'

            elif image_ext == ".cs.png":
                new_file_name = folder_to_save + np.str(image_num) + '_label.png'
            elif image_ext == ".right.cs.png":
                new_file_name = folder_to_save + np.str(image_num) + '_label.png'
            elif image_ext == ".left.cs.png":
                new_file_name = folder_to_save + np.str(image_num) + '_label.png'

            print("Old File: ", old_file_name)
            print("New File: ", new_file_name)

            shutil.copyfile(old_file_name, new_file_name)

    offset += len(files)

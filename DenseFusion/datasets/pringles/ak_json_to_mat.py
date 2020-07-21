import yaml
import glob
import json
import os
import numpy as np
import scipy
import scipy.io as sio
from scipy.spatial.transform import Rotation as R  # scipy>=1.3


'''
=================== TRAIN =================== 
'''
data_dir = '/data/Akeaveny/Datasets/pringles/zed/densefusion/train/'
folder_to_save = 'train/'

output = {}
output['cls_indexes'] = []

# ============= load json ==================
json_files = []
json_addrs = '/data/Akeaveny/Datasets/pringles/zed/densefusion/train/*.json'
images = [json_files.append(file) for file in sorted(glob.glob(json_addrs))]

# ============ output file ================
output = {}

# ================ mat file ===========
for json_file in json_files:
        print(json_file)
        open_json_file = json.load(open(json_file))

        # ================ prelim =========================
        output['cls_indexes'] = [np.asarray([1], dtype=np.uint16)]
        output['camera_scale'] = [np.asarray([1], dtype=np.uint16)]
        output['depth_scale'] = [np.asarray([1000], dtype=np.uint16)]

        # ================ pose =========================

        rot = np.asarray(open_json_file['objects'][1]['pose_transform'])[0:3, 0:3]
        output['rot'] = rot

        translation = np.array(open_json_file['objects'][1]['location']) * 10  # NDDS gives units in centimeters
        output['cam_translation'] = translation

        quaternion = np.asarray(open_json_file['objects'][1]['quaternion_xyzw'])
        output['quaternion'] = quaternion

        quaternion_obj2cam = R.from_quat(np.array(open_json_file['objects'][1]['quaternion_xyzw']))
        quaternion_cam2world = R.from_quat(np.array(open_json_file['camera_data']['quaternion_xyzw_worldframe']))
        quaternion_obj2world = quaternion_obj2cam * quaternion_cam2world
        mirrored_y_axis = np.dot(quaternion_obj2world.as_dcm(), np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
        r = R.from_matrix(mirrored_y_axis)
        output['quaternion1'] = r.as_quat()

        # output['rot1'] = np.dot(rot, np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))

        # trans = np.zeros(shape=(1, 3))
        # translation = open_json_file['objects'][1]['location']
        #
        # poses[0:3, 0:3] = rot[0:3, 0:3]
        # for i in range(0, 3):
        #         # pose[i].append(translation[i])
        #         poses[i, -1] = translation[i]

        # output['trans'] = np.asarray(open_json_file['camera_data']['location_worldframe']) * 10  # NDDS gives units in centimeters
        #
        # quaternion_obj2cam = R.from_quat(np.array(open_json_file['objects'][1]['quaternion_xyzw']))
        # quaternion_cam2world = R.from_quat(np.array(open_json_file['camera_data']['quaternion_xyzw_worldframe']))
        # quaternion_obj2world = quaternion_obj2cam * quaternion_cam2world
        # mirrored_y_axis = np.dot(quaternion_obj2world.as_dcm(), np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
        #
        # output['obj2cam_rotation'] = quaternion_obj2cam.as_dcm()
        # output['obj2cam_rotation1'] = np.dot(quaternion_obj2cam.as_dcm(), np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
        # output['obj2world_rotation'] = quaternion_obj2world.as_dcm()
        # output['obj2world_rotation1'] = mirrored_y_axis

        # ================ mat =========================
        # rmin, rmax, cmin, cmax = get_bbox(mask)
        rmax, cmax = np.asarray(open_json_file['objects'][1]['bounding_box']['top_left'])
        rmin, cmin = np.asarray(open_json_file['objects'][1]['bounding_box']['bottom_right'])
        output['bbox'] = rmin, rmax, cmin, cmax

        # bbox = open_json_file['objects'][1]['bounding_box']
        # bbox_x = round(bbox['top_left'][0])
        # bbox_y = round(bbox['top_left'][1])
        # bbox_w = round(bbox['bottom_right'][0]) - bbox_x
        # bbox_h = round(bbox['bottom_right'][1]) - bbox_y
        # output['bbox1'] = bbox_x, bbox_y, bbox_w, bbox_h

        # ================ camera =========================
        cam_json_file = json.load(open('/data/Akeaveny/Datasets/pringles/zed/_camera_settings.json'))
        output['fx'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['fx'])
        output['fy'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['fy'])
        output['cx'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['cx'])
        output['cy'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['cy'])

        # /data/Akeaveny/Datasets/pringles/Alex/train/images/000000.json
        str_num = json_file.split(folder_to_save)[1]
        str_num = str_num.split(".")[0]

        saved_mat_file = data_dir + np.str(str_num) + '-meta.mat'
        sio.savemat(saved_mat_file, output)

'''
=================== VAL ===================
'''

data_dir = '/data/Akeaveny/Datasets/pringles/zed/densefusion/val/'
folder_to_save = 'val/'

output = {}
output['cls_indexes'] = []

# ============= load json ==================
json_files = []
json_addrs = '/data/Akeaveny/Datasets/pringles/zed/densefusion/val/*.json'
images = [json_files.append(file) for file in sorted(glob.glob(json_addrs))]

# ============ output file ================
output = {}
output['cls_indexes'] = []

# ================ mat file ===========
for json_file in json_files:
        print(json_file)
        open_json_file = json.load(open(json_file))

        # ================ prelim =========================
        output['cls_indexes'] = [np.asarray([1], dtype=np.uint16)]
        output['camera_scale'] = [np.asarray([1], dtype=np.uint16)]
        output['depth_scale'] = [np.asarray([1000], dtype=np.uint16)]

        # ================ pose =========================

        rot = np.asarray(open_json_file['objects'][1]['pose_transform'])[0:3, 0:3]
        output['rot'] = rot

        translation = np.array(open_json_file['objects'][1]['location']) * 10  # NDDS gives units in centimeters
        output['cam_translation'] = translation

        quaternion = np.asarray(open_json_file['objects'][1]['quaternion_xyzw'])
        output['quaternion'] = quaternion

        quaternion_obj2cam = R.from_quat(np.array(open_json_file['objects'][1]['quaternion_xyzw']))
        quaternion_cam2world = R.from_quat(np.array(open_json_file['camera_data']['quaternion_xyzw_worldframe']))
        quaternion_obj2world = quaternion_obj2cam * quaternion_cam2world
        mirrored_y_axis = np.dot(quaternion_obj2world.as_dcm(), np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
        r = R.from_matrix(mirrored_y_axis)
        output['quaternion1'] = r.as_quat()

        # output['rot1'] = np.dot(rot, np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))

        # trans = np.zeros(shape=(1, 3))
        # translation = open_json_file['objects'][1]['location']
        #
        # poses[0:3, 0:3] = rot[0:3, 0:3]
        # for i in range(0, 3):
        #         # pose[i].append(translation[i])
        #         poses[i, -1] = translation[i]

        # output['trans'] = np.asarray(open_json_file['camera_data']['location_worldframe']) * 10  # NDDS gives units in centimeters
        #
        # quaternion_obj2cam = R.from_quat(np.array(open_json_file['objects'][1]['quaternion_xyzw']))
        # quaternion_cam2world = R.from_quat(np.array(open_json_file['camera_data']['quaternion_xyzw_worldframe']))
        # quaternion_obj2world = quaternion_obj2cam * quaternion_cam2world
        # mirrored_y_axis = np.dot(quaternion_obj2world.as_dcm(), np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
        #
        # output['obj2cam_rotation'] = quaternion_obj2cam.as_dcm()
        # output['obj2cam_rotation1'] = np.dot(quaternion_obj2cam.as_dcm(), np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
        # output['obj2world_rotation'] = quaternion_obj2world.as_dcm()
        # output['obj2world_rotation1'] = mirrored_y_axis

        # ================ mat =========================
        # rmin, rmax, cmin, cmax = get_bbox(mask)
        rmax, cmax = np.asarray(open_json_file['objects'][1]['bounding_box']['top_left'])
        rmin, cmin = np.asarray(open_json_file['objects'][1]['bounding_box']['bottom_right'])
        output['bbox'] = rmin, rmax, cmin, cmax

        # bbox = open_json_file['objects'][1]['bounding_box']
        # bbox_x = round(bbox['top_left'][0])
        # bbox_y = round(bbox['top_left'][1])
        # bbox_w = round(bbox['bottom_right'][0]) - bbox_x
        # bbox_h = round(bbox['bottom_right'][1]) - bbox_y
        # output['bbox1'] = bbox_x, bbox_y, bbox_w, bbox_h

        # ================ camera =========================
        cam_json_file = json.load(open('/data/Akeaveny/Datasets/pringles/zed/_camera_settings.json'))
        output['fx'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['fx'])
        output['fy'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['fy'])
        output['cx'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['cx'])
        output['cy'] = np.asarray(cam_json_file['camera_settings'][0]['intrinsic_settings']['cy'])

        # /data/Akeaveny/Datasets/pringles/Alex/train/images/000000.json
        str_num = json_file.split(folder_to_save)[1]
        str_num = str_num.split(".")[0]

        saved_mat_file = data_dir + np.str(str_num) + '-meta.mat'
        sio.savemat(saved_mat_file, output)
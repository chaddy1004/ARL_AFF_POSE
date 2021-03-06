import torch.utils.data as data
from PIL import Image
import os
import os.path
import torch
import numpy as np
import torchvision.transforms as transforms
import argparse
import time
import random
from lib.transformations import quaternion_from_euler, euler_matrix, random_quaternion, quaternion_matrix
import numpy.ma as ma
import copy
import scipy.misc
import scipy.io as scio
import matplotlib.pyplot as plt
import cv2

class PoseDataset(data.Dataset):
    def __init__(self, mode, num_pt, add_noise, root, noise_trans, refine):

        ##################################
        # init path
        ##################################

        if mode == 'train':
            ### clutter
            # self.path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl/dataset_config/data_lists/combined/real_train_data_list.txt'
            self.path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl/dataset_config/data_lists/combined/syn_train_data_list.txt'
            # self.path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl/dataset_config/data_lists/combined/combined_train_data_list.txt'
        elif mode == 'test':
            ### clutter
            # self.path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl/dataset_config/data_lists/combined/real_val_data_list.txt'
            self.path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl/dataset_config/data_lists/combined/syn_val_data_list.txt'
            # self.path = '/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl/dataset_config/data_lists/combined/combined_val_data_list.txt'
        print(self.path)

        self.num_pt = num_pt
        self.root = root
        self.add_noise = add_noise
        self.noise_trans = noise_trans

        ##################################
        # real or syn
        ##################################

        self.list = []
        self.real = []
        self.syn = []
        input_file = open(self.path)
        while 1:
            input_line = input_file.readline()
            if not input_line:
                break
            if input_line[-1:] == '\n':
                input_line = input_line[:-1]
            # self.real.append(input_line)
            self.syn.append(input_line)
            self.list.append(input_line)
        input_file.close()

        self.length = len(self.list)
        self.len_real = len(self.real)
        self.len_syn = len(self.syn)

        print("Loaded: ", len(self.list))
        print("Real Images: ", len(self.real))
        print("SYN Images: ", len(self.syn))

        ##################################
        # IMGAUG
        ##################################

        self.trancolor = transforms.ColorJitter(0.2, 0.2, 0.2, 0.05)
        self.noise_img_loc = 0.0
        self.noise_img_scale = 7.0
        self.minimum_num_pt = 50

        self.norm = transforms.Normalize(mean=[101.922237/255, 101.70265615/255, 101.82904089/255],   ### REAL
                                          std=[63.51475563/255, 63.83739891/255, 62.70252537/255])
        # self.norm = transforms.Normalize(mean=[121.34891436/255, 116.52099986/255, 110.4506291293/255],  ### SYN
        #                                 std=[49.99343061/255, 50.38399108/255, 48.07555426/255])

        ##################################
        # 3D models
        ##################################

        self.symmetry_obj_idx = [1]
        self.num_pt_mesh_small = 500
        self.num_pt_mesh_large = 800
        self.refine = refine

        class_file = open('/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl1/dataset_config/classes.txt')
        class_id_file = open('/home/akeaveny/catkin_ws/src/object-rpe-ak/DenseFusion/datasets/arl1/dataset_config/classes_ids.txt')
        self.class_IDs = np.loadtxt(class_id_file, dtype=np.int32)

        self.cld = {}
        for class_id in self.class_IDs:
            class_input = class_file.readline()
            if not class_input:
                break
            input_file = open('/data/Akeaveny/Datasets/arl_dataset/models/{0}.xyz'.format(class_input[:-1]))
            self.cld[class_id] = []
            while 1:
                input_line = input_file.readline()
                if not input_line:
                    break
                input_line = input_line[:-1].split(' ')
                self.cld[class_id].append([float(input_line[0]), float(input_line[1]), float(input_line[2])])
            self.cld[class_id] = np.array(self.cld[class_id])
            print("class_id: ", class_id)
            print("class_input: ", class_input.rstrip())
            print("Num Point Clouds: {}\n".format(len(self.cld[class_id])))
            input_file.close()

        print("************** LOADED DATASET! **************")

    def __getitem__(self, index):

        ##################################
        # init
        ##################################
        # print('{0}/{1}-meta.mat'.format(self.root, self.list[index]))
        img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        depth = np.array(Image.open('{0}/{1}_depth.png'.format(self.root, self.list[index])))
        label = np.array(Image.open('{0}/{1}_object_id.png'.format(self.root, self.list[index])))
        meta = scio.loadmat('{0}/{1}-meta.mat'.format(self.root, self.list[index]))
        test_folder = '/data/Akeaveny/Datasets/arl_dataset/test_densefusion/'

        # imgaug
        if self.add_noise:
            img = self.trancolor(img)

        # syn image
        img = np.array(img)
        if img.shape[-1] == 4:
            img = img[..., :3]

        ##################################
        # Affordance IDs
        ##################################

        affordance_ids = np.unique(np.array(label))
        # print("affordance_ids: ", affordance_ids)

        ids = []
        for affordance_id in affordance_ids:
            if affordance_id in self.class_IDs:
                ids.append(affordance_id)

        random_idx = np.random.randint(0, len(ids))
        affordance_id = ids[random_idx]

        ##################################

        idx = affordance_id
        # print("idx: ", idx)
        count = 1000 + idx
        meta_idx = str(count)[1:]

        ##################################
        mask_depth = ma.getmaskarray(ma.masked_not_equal(depth, 0))
        mask_label = ma.getmaskarray(ma.masked_equal(label, idx))
        mask = mask_label * mask_depth

        # while 1:
        #     mask_depth = ma.getmaskarray(ma.masked_not_equal(depth, 0))
        #     mask_label = ma.getmaskarray(ma.masked_equal(label, idx))
        #     mask = mask_label * mask_depth
        #     if len(mask.nonzero()[0]) > self.minimum_num_pt:
        #         break

        ############
        # meta
        ############

        # height = meta['width' + meta_idx].flatten().astype(np.int32)[0]
        # width = meta['height' + meta_idx].flatten().astype(np.int32)[0]
        width = meta['object_id_width' + meta_idx].flatten().astype(np.int32)[0]
        height = meta['object_id_height' + meta_idx].flatten().astype(np.int32)[0]

        # self.xmap = np.array([[j for i in range(height)] for j in range(width)])
        # self.ymap = np.array([[i for i in range(height)] for j in range(width)])
        self.xmap = np.array([[j for i in range(width)] for j in range(height)])
        self.ymap = np.array([[i for i in range(width)] for j in range(height)])

        cam_cx = meta['object_id_cx' + meta_idx][0][0]
        cam_cy = meta['object_id_cy' + meta_idx][0][0]
        cam_fx = meta['object_id_fx' + meta_idx][0][0]
        cam_fy = meta['object_id_fy' + meta_idx][0][0]

        cam_scale = np.array(meta['object_id_camera_scale' + meta_idx])[0][0]  # 1000 for depth [mm] to [m]
        border_list = np.array(meta['object_id_border' + meta_idx]).flatten().astype(np.int32)

        cam_rotation4 = np.array(meta['object_id_rot' + meta_idx])
        cam_translation = np.array(meta['object_id_cam_translation' + meta_idx][0])  # in [m]

        ############
        # pred bbox
        ############

        rmin, rmax, cmin, cmax = get_bbox(label, idx, height, width, border_list)
        # print("bbox: ", rmin, rmax, cmin, cmax)

        ############

        img = np.transpose(np.array(img)[:, :, :3], (2, 0, 1))[:, rmin:rmax, cmin:cmax]
        img_masked = np.array(img)

        choose = mask[rmin:rmax, cmin:cmax].flatten().nonzero()[0]

        # print("choose: ", self.num_pt - len(choose))
        if len(choose) == 0:
            print("\n*** CHOOSE IS ZERO ***")
            print('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
            exit(1)

        if len(choose) > self.num_pt:
            c_mask = np.zeros(len(choose), dtype=int)
            c_mask[:self.num_pt] = 1
            np.random.shuffle(c_mask)
            choose = choose[c_mask.nonzero()]
        else:
            choose = np.pad(choose, (0, self.num_pt - len(choose)), 'wrap')

        depth_masked = depth[rmin:rmax, cmin:cmax].flatten()[choose][:, np.newaxis].astype(np.float32)
        xmap_masked = self.xmap[rmin:rmax, cmin:cmax].flatten()[choose][:, np.newaxis].astype(np.float32)
        ymap_masked = self.ymap[rmin:rmax, cmin:cmax].flatten()[choose][:, np.newaxis].astype(np.float32)
        choose = np.array([choose])

        ############
        # cld
        ############

        pt2 = depth_masked / cam_scale
        pt0 = (ymap_masked - cam_cx) * pt2 / cam_fx
        pt1 = (xmap_masked - cam_cy) * pt2 / cam_fy
        cloud = np.concatenate((pt0, pt1, pt2), axis=1)

        translation_noise = np.array([random.uniform(-self.noise_trans, self.noise_trans) for i in range(3)])
        if self.add_noise:
            cloud = np.add(cloud, translation_noise)

        dellist = [j for j in range(0, len(self.cld[idx]))]
        if self.refine:
            dellist = random.sample(dellist, len(self.cld[idx]) - self.num_pt_mesh_large)
        else:
            dellist = random.sample(dellist, len(self.cld[idx]) - self.num_pt_mesh_small)
        model_points = np.delete(self.cld[idx], dellist, axis=0)

        target = np.dot(model_points, cam_rotation4.T)
        if self.add_noise:
            target = np.add(target, cam_translation + translation_noise)
        else:
            target = np.add(target, cam_translation)

        # ######################################
        # ### PROJECT TO SCREEN
        # ######################################
        #
        # cam_mat = np.array([[cam_fx, 0, cam_cx], [0, cam_fy, cam_cy], [0, 0, 1]])
        # dist = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        #
        # cv2_img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        # imgpts, jac = cv2.projectPoints(cloud, np.eye(3), np.zeros(shape=cam_translation.shape), cam_mat, dist)
        # cv2_img = cv2.polylines(np.array(cv2_img), np.int32([np.squeeze(imgpts)]), True, (0, 255, 255))
        # temp_folder = test_folder + 'cv2.cloud.png'
        # cv2.imwrite(temp_folder, cv2_img)
        #
        # cv2_img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        # imgpts, jac = cv2.projectPoints(target, np.eye(3), np.zeros(shape=cam_translation.shape), cam_mat, dist)
        # cv2_img = cv2.polylines(np.array(cv2_img), np.int32([np.squeeze(imgpts)]), True, (0, 255, 255))
        # temp_folder = test_folder + 'cv2.target.png'
        # cv2.imwrite(temp_folder, cv2_img)
        #
        # cv2_img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        # imgpts, jac = cv2.projectPoints(model_points * 1e3, cam_rotation4, cam_translation*1e3, cam_mat, dist)
        # cv2_img = cv2.polylines(np.array(cv2_img), np.int32([np.squeeze(imgpts)]), True, (0, 255, 255))
        # temp_folder = test_folder + 'cv2.model_points.png'
        # cv2.imwrite(temp_folder, cv2_img)
        #
        # cv2_img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        # imgpts, jac = cv2.projectPoints(self.cld[idx] * 1e3, cam_rotation4, cam_translation*1e3, cam_mat, dist)
        # cv2_img = cv2.polylines(np.array(cv2_img), np.int32([np.squeeze(imgpts)]), True, (0, 255, 255))
        # temp_folder = test_folder + 'cv2.1.gt.png'
        # cv2.imwrite(temp_folder, cv2_img)
        #
        # cv2_img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        # imgpts, jac = cv2.projectPoints(self.cld[idx] * 1e3, cam_rotation4, cam_translation*1e3, cam_mat, dist)
        # cv2_img = cv2.polylines(np.array(cv2_img), np.int32([np.squeeze(imgpts)]), True, (0, 255, 255))
        # temp_folder = test_folder + 'cv2.1.gt.png'
        # cv2.imwrite(temp_folder, cv2_img)
        #
        # ######################################
        # ### SAVE IMAGES
        # ######################################
        #
        # img = Image.open('{0}/{1}_rgb.png'.format(self.root, self.list[index]))
        #
        # ### display bbox
        # img_bbox = np.array(img.copy())
        # img_name = test_folder + '1.bbox.png'
        # cv2.rectangle(img_bbox, (cmin, rmin), (cmax, rmax), (255, 0, 0), 2)
        # cv2.imwrite(img_name, img_bbox)
        #
        # p_img = np.transpose(img_masked, (1, 2, 0))
        # temp_folder = test_folder + '1.input.png'
        # scipy.misc.imsave(temp_folder, p_img)
        # temp_folder = test_folder + '1.label.png'
        # scipy.misc.imsave(temp_folder, mask[rmin:rmax, cmin:cmax].astype(np.int32))

        return torch.from_numpy(cloud.astype(np.float32)), \
               torch.LongTensor(choose.astype(np.int32)), \
               self.norm(torch.from_numpy(img_masked.astype(np.float32))), \
               torch.from_numpy(target.astype(np.float32)), \
               torch.from_numpy(model_points.astype(np.float32)), \
               torch.LongTensor([int(idx) - 1])

    def __len__(self):
        return self.length

    def get_sym_list(self):
        return self.symmetry_obj_idx

    def get_num_points_mesh(self):
        if self.refine:
            return self.num_pt_mesh_large
        else:
            return self.num_pt_mesh_small

def get_bbox(label, affordance_id, img_width, img_length, border_list):


    ###################
    # affordance id
    ###################

    rows = np.any(label==affordance_id, axis=1)
    cols = np.any(label==affordance_id, axis=0)
    ### rows = np.any(label, axis=1)
    ### cols = np.any(label, axis=0)

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    rmax += 1
    cmax += 1
    r_b = rmax - rmin
    for tt in range(len(border_list)):
        if r_b > border_list[tt] and r_b < border_list[tt + 1]:
            r_b = border_list[tt + 1]
            break
    c_b = cmax - cmin
    for tt in range(len(border_list)):
        if c_b > border_list[tt] and c_b < border_list[tt + 1]:
            c_b = border_list[tt + 1]
            break
    center = [int((rmin + rmax) / 2), int((cmin + cmax) / 2)]
    rmin = center[0] - int(r_b / 2)
    rmax = center[0] + int(r_b / 2)
    cmin = center[1] - int(c_b / 2)
    cmax = center[1] + int(c_b / 2)
    if rmin < 0:
        delt = -rmin
        rmin = 0
        rmax += delt
    if cmin < 0:
        delt = -cmin
        cmin = 0
        cmax += delt
    if rmax > img_width:
        delt = rmax - img_width
        rmax = img_width
        rmin -= delt
    if cmax > img_length:
        delt = cmax - img_length
        cmax = img_length
        cmin -= delt
    return rmin, rmax, cmin, cmax
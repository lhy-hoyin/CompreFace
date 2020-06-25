#  Version: 2020.02.21
#
#  MIT License
#
#  Copyright (c) 2018 Jiankang Deng and Jia Guo
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# import mxnet as mx
# from mxnet import ndarray as nd
import argparse
import os
import pickle
import sys

import cv2
import numpy as np
import tensorflow as tf
from scipy import misc
from scipy.io import loadmat

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'align'))
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
import detect_face
import face_preprocess


# import lfw

def to_rgb(img):
    w, h = img.shape
    ret = np.empty((w, h, 3), dtype=np.uint8)
    ret[:, :, 0] = ret[:, :, 1] = ret[:, :, 2] = img
    return ret


def IOU(Reframe, GTframe):
    x1 = Reframe[0];
    y1 = Reframe[1];
    width1 = Reframe[2] - Reframe[0];
    height1 = Reframe[3] - Reframe[1];

    x2 = GTframe[0]
    y2 = GTframe[1]
    width2 = GTframe[2] - GTframe[0]
    height2 = GTframe[3] - GTframe[1]

    endx = max(x1 + width1, x2 + width2)
    startx = min(x1, x2)
    width = width1 + width2 - (endx - startx)

    endy = max(y1 + height1, y2 + height2)
    starty = min(y1, y2)
    height = height1 + height2 - (endy - starty)

    if width <= 0 or height <= 0:
        ratio = 0
    else:
        Area = width * height
        Area1 = width1 * height1
        Area2 = width2 * height2
        ratio = Area * 1. / (Area1 + Area2 - Area)
    return ratio


parser = argparse.ArgumentParser(description='Package AgeDB images')
# general
parser.add_argument('--data-dir', default='', help='')
parser.add_argument('--image-size', type=str, default='112,96', help='')
parser.add_argument('--output', default='./', help='path to save.')
args = parser.parse_args()

with tf.Graph().as_default():
    # gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=args.gpu_memory_fraction)
    # sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
    sess = tf.Session()
    with sess.as_default():
        pnet, rnet, onet = detect_face.create_mtcnn(sess, None)

minsize = 20
threshold = [0.6, 0.7, 0.9]
factor = 0.85
# minsize = 15
threshold = [0.6, 0.7, 0.7]
# factor = 0.9
# factor = 0.7

for part in [('04_FINAL_protocol_30_years.mat', 'agedb_30')]:
    mat_file = os.path.join(args.data_dir, part[0])
    mat_data = loadmat(mat_file)
    print(mat_data.__class__)
    data = mat_data['splits']

    bins = []
    issame_list = []
    nrof = [0, 0, 0]
    print('processing', part[1])
    pp = 0
    for i in xrange(data.shape[0]):
        split = data[i][0][0][0][0]
        print(split.shape)
        for c in xrange(split.shape[1]):
            last_name = ''
            for r in xrange(split.shape[0]):
                pp += 1
                if pp % 10 == 0:
                    print('processing', pp, nrof)
                item = split[r][c][0][0]
                path = str(item[0][0])
                vec = path.split('_')
                assert len(vec) >= 5
                name = vec[0]
                if r == 1:
                    issame = False
                    if name == last_name:
                        issame = True
                    print(issame)
                    issame_list.append(issame)
                last_name = name
                age = int(item[1])
                # print(path, age)
                # sys.exit(0)
                img_path = os.path.join(args.data_dir, '03_Protocol_Images', path + ".jpg")
                # print(img_path)
                img = misc.imread(img_path)
                # print(img.shape)
                if img.ndim == 2:
                    img = to_rgb(img)
                img = img[:, :, 0:3]
                _bbox = None
                _landmark = None
                bounding_boxes, points = detect_face.detect_face(img, minsize, pnet, rnet, onet, threshold, factor)
                nrof_faces = bounding_boxes.shape[0]
                if nrof_faces > 0:
                    nrof[0] += 1
                else:
                    bounding_boxes, points = detect_face.detect_face_force(img, minsize, pnet, rnet, onet)
                    nrof_faces = bounding_boxes.shape[0]
                    if nrof_faces > 0:
                        nrof[1] += 1
                    else:
                        nrof[2] += 1
                if nrof_faces > 0:
                    det = bounding_boxes[:, 0:4]
                    img_size = np.asarray(img.shape)[0:2]
                    bindex = 0
                    if nrof_faces > 1:
                        bounding_box_size = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
                        img_center = img_size / 2
                        offsets = np.vstack(
                            [(det[:, 0] + det[:, 2]) / 2 - img_center[1], (det[:, 1] + det[:, 3]) / 2 - img_center[0]])
                        offset_dist_squared = np.sum(np.power(offsets, 2.0), 0)
                        bindex = np.argmax(
                            bounding_box_size - offset_dist_squared * 2.0)  # some extra weight on the centering
                    _bbox = bounding_boxes[bindex, 0:4]
                    _landmark = points[:, bindex].reshape((2, 5)).T
                warped = face_preprocess.preprocess(img, bbox=_bbox, landmark=_landmark, image_size=args.image_size)
                warped = warped[..., ::-1]  # to bgr
                _, s = cv2.imencode('.jpg', warped)
                bins.append(s)
    print(nrof)
    outname = os.path.join(args.output, part[1] + '.bin')
    with open(outname, 'wb') as f:
        pickle.dump((bins, issame_list), f, protocol=pickle.HIGHEST_PROTOCOL)

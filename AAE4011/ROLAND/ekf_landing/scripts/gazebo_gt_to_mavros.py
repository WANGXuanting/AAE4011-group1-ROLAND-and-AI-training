#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import PoseStamped

class GazeboGtToMavros:
    def __init__(self):
        rospy.init_node('gazebo_gt_to_mavros', anonymous=True)
        
        # 获取无人机在Gazebo中的模型名称，默认是 iris0
        self.model_name = rospy.get_param('~model_name', 'iris0')
        
        # 发布到 MAVROS 的外部视觉位姿话题
        self.pub = rospy.Publisher('/mavros/vision_pose/pose', PoseStamped, queue_size=10)
        
        # 订阅 Gazebo 的模型状态
        self.sub = rospy.Subscriber('/gazebo/model_states', ModelStates, self.callback)
        
        rospy.loginfo("Started Gazebo Ground Truth to MAVROS vision_pose relay for model: %s", self.model_name)

    def callback(self, msg):
        try:
            # 在模型列表中找到无人机的索引
            idx = msg.name.index(self.model_name)
            pose = msg.pose[idx]
            
            # 构建 PoseStamped 消息
            pose_stamped = PoseStamped()
            pose_stamped.header.stamp = rospy.Time.now()
            pose_stamped.header.frame_id = "map"
            pose_stamped.pose = pose
            
            # 发布消息
            self.pub.publish(pose_stamped)
        except ValueError:
            # 如果还没生成模型，则忽略
            pass

if __name__ == '__main__':
    try:
        GazeboGtToMavros()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

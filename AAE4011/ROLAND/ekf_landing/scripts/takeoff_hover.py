#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, CommandBoolRequest, SetMode, SetModeRequest

current_state = State()
pose = PoseStamped()
local_pos_pub = None

def state_cb(msg):
    global current_state
    current_state = msg

def publish_setpoint(event):
    """
    【核心修复】后台定时器回调函数：
    独立于主循环，确保以严格的 20Hz 频率持续发布位置指令。
    绝对不会因为请求解锁等操作而造成阻塞断流。
    """
    global pose, local_pos_pub
    if local_pos_pub is not None:
        local_pos_pub.publish(pose)

def main():
    global pose, local_pos_pub
    rospy.init_node('takeoff_hover_node', anonymous=True)

    rospy.Subscriber("mavros/state", State, callback=state_cb)
    local_pos_pub = rospy.Publisher("mavros/setpoint_position/local", PoseStamped, queue_size=10)
    
    rospy.loginfo("等待 MAVROS 服务连接...")
    rospy.wait_for_service("/mavros/cmd/arming")
    arming_client = rospy.ServiceProxy("/mavros/cmd/arming", CommandBool)
    
    rospy.wait_for_service("/mavros/set_mode")
    set_mode_client = rospy.ServiceProxy("/mavros/set_mode", SetMode)

    rate = rospy.Rate(20)

    # 等待飞控连接
    while not rospy.is_shutdown() and not current_state.connected:
        rate.sleep()
    rospy.loginfo("已连接到飞控！等待 EKF 初始化...")

    # 设置目标悬停位置 (x=0, y=0, z=2.0米)
    pose.pose.position.x = 0.0
    pose.pose.position.y = 0.0
    pose.pose.position.z = 2.0

    # 启动后台定时器，以 20Hz (0.05秒) 的频率持续发布悬停点
    rospy.Timer(rospy.Duration(0.05), publish_setpoint)

    # 给飞控一点时间接收初始设定点
    rospy.sleep(1.0)

    offb_set_mode = SetModeRequest()
    offb_set_mode.custom_mode = 'OFFBOARD'
    
    arm_cmd = CommandBoolRequest()
    arm_cmd.value = True

    last_req = rospy.Time.now()

    rospy.loginfo("开始尝试起飞流程...")

    while not rospy.is_shutdown():
        # 1. 先尝试切换 OFFBOARD 模式
        if current_state.mode != "OFFBOARD" and (rospy.Time.now() - last_req) > rospy.Duration(2.0):
            mode_res = set_mode_client.call(offb_set_mode)
            if mode_res.mode_sent:
                rospy.loginfo("🚀 成功切换至 OFFBOARD 模式！")
            last_req = rospy.Time.now()
            
        # 2. 只有在 OFFBOARD 模式下，才尝试解锁起飞
        elif current_state.mode == "OFFBOARD" and not current_state.armed and (rospy.Time.now() - last_req) > rospy.Duration(2.0):
            arm_res = arming_client.call(arm_cmd)
            if arm_res.success:
                rospy.loginfo("✅ 无人机已解锁，正在起飞至 2 米悬停！")
            else:
                rospy.logwarn("❌ 解锁失败！(可能 EKF 未初始化完成，等待重试...)")
            last_req = rospy.Time.now()

        # 主循环只需要休息即可，发布指令的工作已经交给了后台 Timer
        rate.sleep()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass

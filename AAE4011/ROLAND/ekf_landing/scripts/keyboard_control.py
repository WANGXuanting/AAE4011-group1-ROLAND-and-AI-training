#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import sys, select, termios, tty
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, CommandBoolRequest, SetMode, SetModeRequest

# 全局变量
current_state = State()
pose = PoseStamped()
local_pos_pub = None

# 终端设置（用于非阻塞读取键盘）
settings = termios.tcgetattr(sys.stdin)

msg = """
================================
   无人机键盘控制面板 (OFFBOARD)
================================
操作指南:
  1 : 准备 (切入 OFFBOARD 并解锁)
  t : 起飞 (自动升至 2米 高度)
  
飞行控制:
  w : 向前飞 (+x)      i : 升高 (+z)
  s : 向后飞 (-x)      k : 降低 (-z)
  a : 向左飞 (+y)
  d : 向右飞 (-y)

  l : 降落 (切换至 AUTO.LAND 模式)
  q : 退出程序
================================
"""

def getKey():
    """非阻塞获取键盘按键"""
    tty.setraw(sys.stdin.fileno())
    # 将超时时间改为 0.05 秒，以匹配 20Hz 的主循环频率
    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def state_cb(msg):
    global current_state
    current_state = msg

def main():
    global pose, local_pos_pub
    rospy.init_node('keyboard_control_node', anonymous=True)

    rospy.Subscriber("mavros/state", State, callback=state_cb)
    local_pos_pub = rospy.Publisher("mavros/setpoint_position/local", PoseStamped, queue_size=10)
    
    arming_client = rospy.ServiceProxy("/mavros/cmd/arming", CommandBool)
    set_mode_client = rospy.ServiceProxy("/mavros/set_mode", SetMode)

    # 初始设定点 (地面)
    pose.header.frame_id = "map"
    pose.pose.position.x = 0.0
    pose.pose.position.y = 0.0
    pose.pose.position.z = 0.0

    rospy.loginfo("等待飞控连接...")
    while not rospy.is_shutdown() and not current_state.connected:
        rospy.sleep(0.1)
    rospy.loginfo("飞控已连接！")

    print(msg)
    
    step = 0.5 # 每次按键移动的步长 (米)
    
    # 设置主循环频率为 20Hz
    rate = rospy.Rate(20)

    try:
        while not rospy.is_shutdown():
            # 1. 强制在主循环中以 20Hz 持续发布设定点，防止 Failsafe
            pose.header.stamp = rospy.Time.now()
            local_pos_pub.publish(pose)

            # 2. 获取键盘输入
            key = getKey()
            
            if key == '1':
                # 切换 OFFBOARD 并解锁
                rospy.loginfo("正在请求 OFFBOARD 模式并解锁...")
                set_mode_client.call(SetModeRequest(custom_mode='OFFBOARD'))
                rospy.sleep(3)
                arming_client.call(CommandBoolRequest(value=True))
                
            elif key == 't':
                # 起飞
                pose.pose.position.z = 2.0
                rospy.loginfo("起飞指令已发送！目标高度: 2.0m")
                
            elif key == 'w':
                pose.pose.position.x += step
                rospy.loginfo(f"向前移动: x={pose.pose.position.x}")
            elif key == 's':
                pose.pose.position.x -= step
                rospy.loginfo(f"向后移动: x={pose.pose.position.x}")
            elif key == 'a':
                pose.pose.position.y += step
                rospy.loginfo(f"向左移动: y={pose.pose.position.y}")
            elif key == 'd':
                pose.pose.position.y -= step
                rospy.loginfo(f"向右移动: y={pose.pose.position.y}")
            elif key == 'i':
                pose.pose.position.z += step
                rospy.loginfo(f"升高: z={pose.pose.position.z}")
            elif key == 'k':
                pose.pose.position.z = max(0.0, pose.pose.position.z - step) # 防止钻入地下
                rospy.loginfo(f"降低: z={pose.pose.position.z}")
                
            elif key == 'l':
                # 降落
                rospy.loginfo("请求降落 (AUTO.LAND)...")
                set_mode_client.call(SetModeRequest(custom_mode='AUTO.LAND'))
                
            elif key == 'q' or key == '\x03': # \x03 是 Ctrl+C
                rospy.loginfo("退出程序...")
                break
            
            # 3. 维持 20Hz 循环频率
            rate.sleep()

    except Exception as e:
        print(e)
    finally:
        # 恢复终端设置
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

if __name__ == '__main__':
    main()

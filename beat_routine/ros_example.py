import rclpy
from rclpy.node import Node
from ros2_unitree_legged_msgs.msg import HighCmd
import time
#    2 source /opt/ros/humble/setup.bash
#    3 source /home/lalu/Vellav/Robot_Rave_Hackathon/ros2_ws/install/local_setup.bash
#    4 
#    5 # Now, run your Python script
#    6 python3 /home/lalu/Vellav/Robot_Rave_Hackathon/go1pylib/beat_routine/ros_example.py
class RobotWalkNode(Node):
    """
    This node demonstrates direct, low-level control of the Go1 robot by publishing
    messages directly to the /high_cmd topic. It does not use the go1pylib abstraction.
    """
    def __init__(self):
        super().__init__('robot_walk_node')
        self.publisher_ = self.create_publisher(HighCmd, '/high_cmd', 10)
        self.get_logger().info('Low-level ROS walk node started. Publishing commands...')

    def send_walk_command(self, vx=0.0, vy=0.0, yaw_speed=0.0):
        """Creates and publishes a HighCmd message."""
        msg = HighCmd()
        
        # Mode 2 is for walking
        msg.mode = 2
        msg.gait_type = 1
        msg.speed_level = 0
        msg.foot_raise_height = 0.0
        
        # Set velocities
        msg.velocity[0] = float(vx)
        msg.velocity[1] = float(vy)
        msg.yaw_speed = float(yaw_speed)
        
        # Body height and posture can also be set, leaving as 0 for default
        msg.body_height = 0.0
        msg.foot_raise_height = 0.0
        
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published HighCmd: mode=2, vx={vx}, vy={vy}')


def main(args=None):
    rclpy.init(args=args)
    
    walk_node = RobotWalkNode()
    
    # Give a moment for publishers to connect
    time.sleep(1.0)
    
    # 1. Send command to walk forward
    walk_node.send_walk_command(vx=0.2)
    
    # 2. Let the robot walk for 2 seconds
    time.sleep(2.0)
    
    # 3. Send command to stop
    walk_node.send_walk_command(vx=0.0)
    
    # Allow the stop command to be processed
    time.sleep(1.0)
    
    walk_node.destroy_node()
    rclpy.shutdown()
    print("Script finished.")


if __name__ == '__main__':
    main()

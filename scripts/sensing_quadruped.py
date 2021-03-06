#----------------------------
# CONSTANTS FOR CALIBRATION
#----------------------------
TEST = False

INCREMENTS = 40
WALK_STEPS = 5
DELAY = 0.25

TWIST_HIP = 30

KNEE_BENTUP = 10
ANKLE_BENTUP = -10

HIP_SIDESTEP = -60
KNEE_SIDESTEP = -30
ANKLE_SIDESTEP = 40

HIP_REACH = 10
KNEE_REACH = -25
ANKLE_REACH = 40

HIP_REST = -10
KNEE_REST = -30
ANKLE_REST = 40

#----------------------------
# PACKAGES, HELPERS, DRIVER SETUP
#----------------------------
from time import sleep

if TEST == False:
  from comm.pwm import PWM
  driver = PWM(0x41)
  driver.setPWMFreq(50)

# Note: These should be enums
FRONT_LEFT = 'front left'
FRONT_RIGHT = 'front right'
BACK_LEFT = 'back left'
BACK_RIGHT = 'back right'

if TEST == True:
  DELAY = 0.0

def map(z, x, y, a, b):
  # x to y is the old range
  # a to b is the new range
  # z is somewhere in between x and y
  # c is somewhere in between a and b
  c = (z - x) * (b - a) / (y - x) + a
  return c

#----------------------------
# QUADRUPED JOINT
#----------------------------
class Joint:
  def __init__(self, channel, pwm_min, pwm_max, angle_min, angle_max):
    self.channel = channel

    # min,and max pwm values
    self.pwm_min = pwm_min
    # the 'min_pwm' pwm signal corresponds to:
    #   hip: towards the sides and away from either the back or front
    #   knee: upper leg towards ground
    #   ankle: lower leg towards the upper leg from the perpendicular
    self.pwm_max = pwm_max
    # the 'pwm_max' pwm signal corresponds to:
    #   hip: away from the sides and towards either back or front
    #   knee: upper leg towards the sky
    #   ankle: lowerleg away from the upper leg from the perpendicular

    # min,and max values in degrees
    # angle_min is negative, corresponds to 'pwm_min'
    self.angle_min = angle_min
    # angle_max is positive, corresponds to 'pwm_max'
    self.angle_max = angle_max
    self.pose(0)

  def pose(self, angle):
    pwm_value = map(angle, self.angle_min, self.angle_max, self.pwm_min, self.pwm_max)
    #print 'POSE ch: ', self.channel, 'angle: ', angle, 'pwm:', int(pwm_value)
    if TEST == False:
      driver.setPWM(self.channel, 0, int(pwm_value))
    self.current_angle = angle

  def get_movement_increment(self, target_angle, increments):
    return (target_angle - self.current_angle) / increments

  def move_by(self, da):
    self.pose(self.current_angle + da)

  def off(self):
    if TEST == False:
      driver.setPWM(self.channel, 0, 0)

#----------------------------
# QUADRUPED CORE STANCES
#----------------------------
class QuadrupedCore:
  def __init__(self, legs):
    self.legs = legs
    self.fast_zero_pose()

  def off(self):
    for joints in self.legs.values():
      for joint in joints.values():
        joint.off()

  def fast_zero_pose(self, delay=0):
    for joints in self.legs.values():
      for joint in joints.values():
        joint.pose(0)

  def zero_pose(self, delay=DELAY):
    final_angles = {
      'front left': {'hip': 0, 'knee': 0, 'ankle': 0},
      'front right': {'hip': 0, 'knee': 0, 'ankle': 0},
      'back left': {'hip': 0, 'knee': 0, 'ankle': 0},
      'back right': {'hip': 0, 'knee': 0, 'ankle': 0}
    }
    self.propel_slowly(final_angles, delay)

  def pose(self, position, hip_angle, knee_angle, ankle_angle, delay):
    self.legs[position]['hip'].pose(hip_angle)
    self.legs[position]['knee'].pose(knee_angle)
    self.legs[position]['ankle'].pose(ankle_angle)
    sleep(delay)

  def slow_pose(self, position, hip_angle, knee_angle, ankle_angle, delay):
    hip = self.legs[position]['hip']
    knee = self.legs[position]['knee']
    ankle = self.legs[position]['ankle']

    dh = hip.get_movement_increment(hip_angle, INCREMENTS)
    dk = knee.get_movement_increment(knee_angle, INCREMENTS)
    da = ankle.get_movement_increment(ankle_angle, INCREMENTS)

    dt = delay / INCREMENTS

    for _ in range(INCREMENTS):
      hip.move_by(dh)
      knee.move_by(dk)
      ankle.move_by(da)
      sleep(dt)

  def bend_up(self, position, delay=0):
    knee = self.legs[position]['knee']
    ankle = self.legs[position]['ankle']

    dk = knee.get_movement_increment(KNEE_BENTUP, INCREMENTS)
    da = ankle.get_movement_increment(ANKLE_BENTUP, INCREMENTS)
    dt = delay / INCREMENTS

    for _ in range(INCREMENTS):
      knee.move_by(dk)
      ankle.move_by(da)
      sleep(dt)

  def move_joints_simultaneously(self, hip_angle, knee_angle, ankle_angle, delay):
    dt = delay / INCREMENTS
    d_angles = {}

    for position, joints in self.legs.items():
      dh = joints['hip'].get_movement_increment(hip_angle, INCREMENTS)
      dk = joints['knee'].get_movement_increment(knee_angle, INCREMENTS)
      da = joints['ankle'].get_movement_increment(ankle_angle, INCREMENTS)

      d_angles[position] = {
        'hip': dh,
        'knee': dk,
        'ankle': da
      }

    for _ in range(INCREMENTS):
      for position, joints in self.legs.items():

        dh = d_angles[position]['hip']
        dk = d_angles[position]['knee']
        da = d_angles[position]['ankle']

        joints['hip'].move_by(dh)
        joints['knee'].move_by(dk)
        joints['ankle'].move_by(da)

        sleep(dt)

  def rest(self, position, delay=0):
    self.slow_pose(position, HIP_REST, KNEE_REST, ANKLE_REST, delay)

  def side_step(self, position, delay=0):
    self.slow_pose(position, HIP_SIDESTEP, KNEE_SIDESTEP, ANKLE_SIDESTEP, delay)

  def reach(self, position, delay=0):
    self.slow_pose(position, HIP_REACH, KNEE_REACH, ANKLE_REACH, delay)

  def high_pose_simultaneously(self, delay):
    self.move_joints_simultaneously(0, -80, 80, delay)

  def rest_pose_simultaneously(self, delay):
    self.move_joints_simultaneously(HIP_REST, KNEE_REST, ANKLE_REST, delay)

  def propel_slowly(self, final_angles, delay):
    # --------
    # find by how much to increment each joint
    # given the current angle, final angle and number of increments
    # --------
    d_angles = {}
    for position, joints in self.legs.items():

      hip_angle = final_angles[position]['hip']
      knee_angle = final_angles[position]['knee']
      ankle_angle = final_angles[position]['ankle']

      dh = joints['hip'].get_movement_increment(hip_angle, INCREMENTS)
      dk = joints['knee'].get_movement_increment(knee_angle, INCREMENTS)
      da = joints['ankle'].get_movement_increment(ankle_angle, INCREMENTS)

      d_angles[position] = {
        'hip': dh,
        'knee': dk,
        'ankle': da
      }

    # --------
    # each of the 18 angles should incrementally
    # move a little, at each increment count
    # --------
    dt = delay / INCREMENTS
    for _ in range(INCREMENTS):
      for position, joints in self.legs.items():

        dh = d_angles[position]['hip']
        dk = d_angles[position]['knee']
        da = d_angles[position]['ankle']

        joints['hip'].move_by(dh)
        joints['knee'].move_by(dk)
        joints['ankle'].move_by(da)

        sleep(dt)

  def propel_slowly_back_left_reaching(self, delay=0):
    final_angles = {
      'front left': {'hip': HIP_SIDESTEP, 'knee': KNEE_SIDESTEP, 'ankle': ANKLE_SIDESTEP},
      'front right': {'hip': HIP_REST, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
      'back left': {'hip': HIP_REACH, 'knee': KNEE_REACH, 'ankle': ANKLE_REACH},
      'back right': {'hip': HIP_REST, 'knee': KNEE_REST, 'ankle': ANKLE_REST}
    }
    self.propel_slowly(final_angles, delay)

  def propel_slowly_back_right_reaching(self, delay=0):
    final_angles = {
      'front left': {'hip': HIP_REST, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
      'front right': {'hip': HIP_SIDESTEP, 'knee': KNEE_SIDESTEP, 'ankle': ANKLE_SIDESTEP},
      'back left': {'hip': HIP_REST, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
      'back right': {'hip': HIP_REACH, 'knee': KNEE_REACH, 'ankle': ANKLE_REACH}

    }
    self.propel_slowly(final_angles, delay)

#----------------------------
# QUADRUPED JOINT SETUP
#----------------------------
ANGLE_MIN = -70
ANGLE_MAX = 70

hip_front_left = Joint(channel=0, pwm_min=140, pwm_max=460, angle_min=ANGLE_MIN, angle_max=ANGLE_MAX)
hip_front_right = Joint(3, 490, 160, ANGLE_MIN, ANGLE_MAX)
hip_back_left = Joint(6, 485, 160, ANGLE_MIN, ANGLE_MAX)
hip_back_right = Joint(9, 190, 510, ANGLE_MIN, ANGLE_MAX)
knee_front_left = Joint(1, 150, 480, ANGLE_MIN, ANGLE_MAX)
knee_front_right = Joint(4, 440, 120, ANGLE_MIN, ANGLE_MAX)
knee_back_left = Joint(7, 460, 140, ANGLE_MIN, ANGLE_MAX)
knee_back_right = Joint(10, 170, 480, ANGLE_MIN, ANGLE_MAX)
ankle_front_left = Joint(2, 485, 170, ANGLE_MIN, ANGLE_MAX)
ankle_front_right = Joint(5, 150, 480, ANGLE_MIN, ANGLE_MAX)
ankle_back_left = Joint(8, 170, 480, ANGLE_MIN, ANGLE_MAX)
ankle_back_right = Joint(11, 470, 160, ANGLE_MIN, ANGLE_MAX)

LEG_1 = {
  'hip': hip_front_left,
  'knee': knee_front_left,
  'ankle': ankle_front_left
}

LEG_2 = {
  'hip': hip_front_right,
  'knee': knee_front_right,
  'ankle': ankle_front_right
}

LEG_3 = {
  'hip': hip_back_left,
  'knee': knee_back_left,
  'ankle': ankle_back_left
}

LEG_4 = {
  'hip': hip_back_right,
  'knee': knee_back_right,
  'ankle': ankle_back_right
}

#----------------------------
# WALK ALGORITHMS STARTS HERE
#----------------------------
def walk(robot, steps):

  robot.zero_pose(DELAY)
  robot.rest_pose_simultaneously(DELAY)

  # STEP ZERO
  # Go to starting position
  # from neutral (all 0 degrees)
  # side step backward of front right leg
  robot.side_step(FRONT_RIGHT, DELAY)

  for _ in range(steps):

    # from starting position
    # side step forward of back right leg
    print('step 1')
    robot.bend_up(BACK_RIGHT, DELAY)
    robot.side_step(BACK_RIGHT, DELAY)

    # reach forward of front right leg
    print('step 2')
    robot.bend_up(FRONT_RIGHT, DELAY)
    robot.reach(FRONT_RIGHT, DELAY)

    # propel the body forward by moving all four legs backward
    print('step 3')
    robot.propel_slowly_back_left_reaching(DELAY)
    sleep(DELAY)

    # side step forward of left back leg
    print('step 4')
    robot.bend_up(BACK_LEFT, DELAY)
    robot.side_step(BACK_LEFT, DELAY)

    # reach forward of left front leg
    print('step 5')
    robot.bend_up(FRONT_LEFT, DELAY)
    robot.reach(FRONT_LEFT, DELAY)

    # propel the body forward by moving all four legs backward
    print('step 6')
    robot.propel_slowly_back_right_reaching(DELAY)

  robot.rest_pose_simultaneously(DELAY)
  robot.high_pose_simultaneously(DELAY)
  robot.off()


def walk_forward(steps=WALK_STEPS):
  LEGS = {
    'front left': LEG_1,
    'front right': LEG_2,
    'back left': LEG_3,
    'back right': LEG_4
  }

  print('Walk forward.......')
  robot = QuadrupedCore(LEGS)
  walk(robot, steps)


def walk_backward(steps=WALK_STEPS):
  LEGS = {
    'front left': LEG_4,
    'front right': LEG_3,
    'back left': LEG_2,
    'back right': LEG_1
  }

  print('Walk backward.......')
  robot = QuadrupedCore(LEGS)
  walk(robot, steps)


def rotate(twist_angles, steps):
  LEGS = {
    'front left': LEG_1,
    'front right': LEG_2,
    'back left': LEG_3,
    'back right': LEG_4
  }

  robot = QuadrupedCore(LEGS)

  robot.zero_pose(DELAY)
  robot.rest_pose_simultaneously(DELAY)

  for _ in range(steps):
    print("Twist.")
    robot.propel_slowly(twist_angles, DELAY)

    for leg_position in [FRONT_LEFT, BACK_LEFT, BACK_RIGHT, FRONT_RIGHT]:
      print("Replant one foot.")
      robot.rest(leg_position, DELAY)

  robot.zero_pose(DELAY)
  robot.rest_pose_simultaneously(DELAY)
  robot.high_pose_simultaneously(DELAY)
  robot.off()


def rotate_cw(steps=WALK_STEPS):
  twist_angles = {
    'front left': {'hip': -TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
    'front right': {'hip': TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
    'back left': {'hip': TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
    'back right': {'hip': -TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST}
  }
  print('Rotate clockwise')
  rotate(twist_angles, steps)


def rotate_ccw(steps=WALK_STEPS):
  twist_angles = {
    'front left': {'hip': TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
    'front right': {'hip': -TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
    'back left': {'hip': -TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST},
    'back right': {'hip': TWIST_HIP, 'knee': KNEE_REST, 'ankle': ANKLE_REST}
  }
  print('Rotate counterclockwise')
  rotate(twist_angles, steps)

def make_robot():
  LEGS = {
    'front left': LEG_1,
    'front right': LEG_2,
    'back left': LEG_3,
    'back right': LEG_4
  }

  robot = QuadrupedCore(LEGS)
  return robot

# -----------------------
# IMPORTANT: LOOK HERE!
# -----------------------

#  - 0 = Channel 0 minus channel 1
#  - 1 = Channel 0 minus channel 3
#  - 2 = Channel 1 minus channel 3
#  - 3 = Channel 2 minus channel 3
CHANNEL_DIFF_ENV_SENSOR = 3
CHANNEL_PERIMETER0 = 0
CHANNEL_PERIMETER1 = 1

SENSOR_I2C_ADDRESS = 0x48
I2C_BUS_NUM = 1
GAIN = 1
SENSOR_DATA_RATE = 128

ENV_SENSOR_THRESHOLD = 1000
STEPS = 2

# forward, backward, rotate_cw, rotate_ccw threshold
VAL_0 = -75
VAL_1 = 50
VAL_2 = 225

import time
seconds = time.time()
print("Seconds since epoch =", seconds)	

NUMBER_OF_SECONDS_RUNNING = 240
NUMBER_OF_SECONDS_REST = 120

if TEST == False:
  import Adafruit_ADS1x15
  # https://github.com/adafruit/Adafruit_Python_ADS1x15
  adc = Adafruit_ADS1x15.ADS1115(address=SENSOR_I2C_ADDRESS, busnum=I2C_BUS_NUM)

  while True:
    start_of_timer = time.time()
    
    while time.time() - start_of_timer < NUMBER_OF_SECONDS_RUNNING:
      
      env_sensor_value = adc.read_adc_difference(CHANNEL_DIFF_ENV_SENSOR, gain=GAIN)
      perimeter_sensor0_value = adc.read_adc(CHANNEL_PERIMETER0, gain=GAIN)
      perimeter_sensor1_value = adc.read_adc(CHANNEL_PERIMETER1, gain=GAIN)

      print("perimeter_sensor0_value: ", perimeter_sensor0_value)
      print("perimeter_sensor1_value: ", perimeter_sensor1_value)
      print("env_sensor_value: ", env_sensor_value)

      # Change this to be greater than or less than
      if perimeter_sensor0_value > ENV_SENSOR_THRESHOLD or perimeter_sensor1_value > ENV_SENSOR_THRESHOLD:
        walk_backward(steps=STEPS)
      elif env_sensor_value <= VAL_0:
        rotate_cw(steps=STEPS)
      elif VAL_0 < env_sensor_value <= VAL_1:
        rotate_ccw(steps=STEPS)
      elif VAL_1 < env_sensor_value <= VAL_2:
        walk_forward(steps=STEPS)
      else:
        walk_backward(steps=STEPS)
    
    robot = make_robot()
    robot.rest_pose_simultaneously(DELAY)
    robot.high_pose_simultaneously(DELAY) 
    
    robot.off()
    sleep(NUMBER_OF_SECONDS_REST)

from comm.pwm import PWM
from time import sleep

# CALIBRATION

driver = PWM(0x41)
driver.setPWMFreq(50)
 
print("Hello world!")
print("Turning off all the 12 servos...")

for ch in range(12):
  driver.setPWM(ch, 0, 0)
  pass

print("...done.")


def get_channel():
  ch = 0
  while True:
    ch = input("Input which channel you want to calibrate (0-11): ")
    try:
      ch = int(ch)
    except:
      print("That is not an integer. Try again.")
      continue

    if ch >= 0 and ch < 12:
      break

    print("Please input a number from 0 to 11.")

  return ch


def get_pwm_value():
  val = 0

  while True:
    val= input("Input pwm value you want to try: ")
    try:
      val = int(val)
    except:
      print("That is not an integer. Try again.")
      continue

    if val >= 0 :
      break

    print("Please input a positive number.")

  return val


seconds = 2.0

while True:
  ch = get_channel()
  while True:
    val = get_pwm_value()

    print(f"Setting pwm value of channel {ch} to {val} for {seconds} second(s)...")
    driver.setPWM(ch, 0, val)
    sleep(seconds)
    
    print("...done.")
    print('Turning that servo off...')
    driver.setPWM(ch, 0, 0)
    
    print("...done.")
    print("Do you want to calibrate a different channel?")
    print("press y if so.")
    print("or press enter to calibrate the same channel.")
    should_change = input("y/_: ")

    if should_change == 'y':
      break

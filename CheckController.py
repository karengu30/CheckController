import time
import datetime
from MonitorController import MonitorController

# Send summary emails at 9am and 6pm
# Send update email as soon as Pi breaks

while True:
    print(datetime.datetime.now())
    if datetime.datetime.now().hour == 9 and datetime.datetime.now().minute<20 or datetime.datetime.now().hour == 18 and datetime.datetime.now().minute<20:
        monitor2 = MonitorController('summary')  # condition 2 = send summary email
        time.sleep(20*60) # wait for 20 min to pass until not 9am or 6pm so continuous monitoring can continue
    else:
        monitor1 = MonitorController('continuous')  # condition 1 = continuous monitoring for pis
        time.sleep(60*15) # checking every 15 minutes

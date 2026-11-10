"""Prevent idle sleep on weekdays 09:00–17:00 in the Mac's local timezone."""
import datetime,math,os,subprocess

def remaining_seconds(now):
    if now.weekday() >= 5 or not 9 <= now.hour < 17:
        return 0
    return max(0,math.ceil((now.replace(hour=17,minute=0,second=0,microsecond=0)-now).total_seconds()))

def agent_config(root):
    return {'Label':'com.mouselab.workday-awake','ProgramArguments':[str(root/'.venv/bin/python3'),'-m','scripts.deployment.workday_awake'],'WorkingDirectory':str(root),'RunAtLoad':True,'StartInterval':60,'StartCalendarInterval':[{'Weekday':day,'Hour':9,'Minute':0} for day in range(1,6)],'StandardOutPath':str(root/'logs/workday-awake.log'),'StandardErrorPath':str(root/'logs/workday-awake-error.log'),'Umask':63}

def main():
    now=datetime.datetime.now().astimezone()
    seconds=remaining_seconds(now)
    if seconds:
        # No display assertion. -s also prevents AC-powered system/maintenance sleep.
        # -w releases both assertions if this job stops.
        print(f'{now.isoformat()} Preventing idle sleep until 17:00 local time',flush=True)
        subprocess.run(['/usr/bin/caffeinate','-is','-t',str(seconds),'-w',str(os.getpid())],check=True)

if __name__=='__main__':main()

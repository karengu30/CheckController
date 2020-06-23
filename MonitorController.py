import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
# modules for emails
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart


class MonitorController:
    def __init__(self, condition):
        print('In Initialize')
        # Identify credential files (Credential files for uploading updates to Google Drive are found here)
        self.credentialSpreadsheet = 'SAcredentials.json'
        # Identify UN, PW, and recipients (should be in file called email_info.txt)
        # If adding recipients, add directly to email_info.txt file
        lines = []
        with open('email_info.txt', 'r') as f:
            lines = f.readlines()
        lines = [i.split('\n', 1)[0] for i in lines] # removes \n at end of each line
        for item in lines:
            if 'username' in item:
                self.username = item.split(': ')[1]
            elif 'password' in item:
                self.password = item.split(': ')[1]
            elif 'recipients' in item:
                self.recipients = item.split(': ')[1].split(',') # list of recipients

        # try check if files exist, except make the files
        try:
            print("checking if txt files exist")
            open('bad_pi.txt', 'r').close()
            open('bad_pi.html', 'r').close()
        except:
            print("no text file exists. writing new ones")
            open('bad_pi.txt', 'w').close()
            open('bad_pi.html', 'w').close()

        while True:
            print("WHILE TRUE")
            # Connect to Google Spreadsheets
            self._authenticateGoogleSpreadSheets() # Creates self.controllerGS, and self.alldata_noheader
            pi_ws = self.controllerGS.worksheet('RaspberryPi')

            alldata = pi_ws.get_all_values()  # gives list of lists of rows

            self.alldata_noheader = alldata[1:]
            self.headers = pi_ws.row_values(1)
            print('Authenticated')
            self.rpID = self.headers.index('RaspberryPiID')
            self.tankID = self.headers.index('TankID')
            self.projectID = self.headers.index('ProjectID')
            self.status = self.headers.index('Status')
            self.error = self.headers.index('Error')
            self.ping = self.headers.index('Ping')

            self.not_empty = []
            for row in self.alldata_noheader: #take out empty rows
                if row[self.rpID].strip() != '':
                    self.not_empty.append(row)

            if condition == 'continuous': # continuous update checker
                self.bad_pi = []
                for row in self.not_empty: # identify if there are any bad pis
                    ping_dtobj = datetime.datetime.strptime(row[self.ping], "%Y-%m-%d %H:%M:%S")  #changes ping string back to datetime object
                    # checking if status is running and the last ping was more than 15 min ago
                    if row[self.status] == "Running" and datetime.datetime.now() - ping_dtobj > datetime.timedelta(minutes = 15):
                        self.bad_pi.append(row)

                print(str(len(self.bad_pi)))

                if len(self.bad_pi) != 0: # at least one bad pi present
                    flag = self._check_same() # check if email already sent

                    if flag == False: # means at least one bad pi did not match the ones already in the file so email sent
                        self._write_message('continuous_write')
                        self._email('continuous')
                    elif flag == True:
                        break
                else:  # there were 0 bad pis and no email sent
                    self._write_message('clear')
                    print("All pis good")

            elif condition == 'summary': # summarizes any pis not running. currently does not include running pis with bad ping
                self.not_running = []
                for row in self.not_empty:
                    if row[self.status] != "Running":
                        self.not_running.append(row)
                self._write_message('summary_write')
                self._email('summary')

            print("BEFORE BREAK")
            break

    def _check_same(self):  #checks bad_pi and past email file
        print("CHECK SAME")
        flag = True    # assumes no change so no email

        with open('bad_pi.txt', 'r') as tf:  #gets previous email contents
            lines = tf.readlines()
            print(lines)

        past_badPI = 0
        for item in lines:  # count how many bad pi were in last email
            if 'RaspberryPiID: ' in item:
                past_badPI += 1

        if past_badPI != len(self.bad_pi):  #if different # of pis, then send email
            flag = False
        else:
            count = 0
            while flag == True and count < past_badPI:
                for pi in self.bad_pi:
                    name = 'RaspberryPiID: ' + pi[self.rpID] + '\n'
                    flag = name in lines  # True means bad_pi was in the file, False means bad_pi was not in file
                    count += 1

                    print(str(flag))

        print('CHECK SAME END')
        print(str(flag))
        return flag

    def _write_message(self, condition):  # clear, continuous_write, or summary_write
        if condition == 'clear': # clear the file if 0 bad pis
            open('bad_pi.txt', 'w').close()
            open('bad_pi.html', 'w').close()
            print('CLEARED')

        elif condition == 'continuous_write':
            text_file = open('bad_pi.txt', 'w')
            html_file = open('bad_pi.html', 'w')

            text = ""
            html = "<html><head></head><body><p>"

            for pi in self.bad_pi:
                text += ('\n' + 'RaspberryPiID: ' + pi[self.rpID] + '\n' +
                        'TankID: ' + pi[self.tankID] + '\n' +
                        'ProjectID: ' + pi[self.projectID] + '\n' +
                        'Ping: ' + pi[self.ping] + '\n')
                html += ('<br>' + 'RaspberryPiID: ' + pi[self.rpID] + '<br>' +
                        'TankID: ' + pi[self.tankID] + '<br>' +
                        'ProjectID: ' + pi[self.projectID] + '<br>' +
                        'Ping: ' + pi[self.ping] + '<br>')

            text_file.write(text)
            html += "</p></body></html>"
            html_file.write(html)

            text_file.close()
            html_file.close()

        elif condition == 'summary_write':
            text_file = open('summary.txt', 'w')
            html_file = open('summary.html', 'w')
            text = ""
            html = "<html><head></head><body><p>"

            text += ('Total Pis = ' + str(len(self.not_empty)) + '\n' +
                    'Pis Running = ' + str(len(self.not_empty) - len(self.not_running)) + '\n' +
                    'Pis Not Running = ' + str(len(self.not_running)) + '\n')
            html += ('Total Pis = ' + str(len(self.not_empty)) + '<br>' +
                    'Pis Running = ' + str(len(self.not_empty) - len(self.not_running)) + '<br>' +
                    'Pis Not Running = ' + str(len(self.not_empty)) + '<br>')

            for pi in self.not_running:
                text += ('\n' + 'RaspberryPiID: ' + pi[self.rpID] + '\n' +
                        'TankID: ' + pi[self.tankID] + '\n' +
                        'ProjectID: ' + pi[self.projectID] + '\n' +
                        'Status: ' + pi[self.status] + '\n' +
                        'Error: ' + pi[self.error] + '\n')
                html += ('<br>' + 'RaspberryPiID: ' + pi[self.rpID] + '<br>' +
                        'TankID: ' + pi[self.tankID] + '<br>' +
                        'ProjectID: ' + pi[self.projectID] + '<br>' +
                        'Status: ' + pi[self.status] + '<br>' +
                        'Error: ' + pi[self.error] + '<br>')

            text_file.write(text)
            html += "</p></body></html>"
            html_file.write(html)

            text_file.close()
            html_file.close()


    def _email(self, condition):
        msg = MIMEMultipart()

        if condition == 'continuous':
            msg['Subject'] = 'Pi Updates: ' + str(len(self.bad_pi)) + " need attention"
            msg['From'] = self.username
            msg['To'] = ", ".join(self.recipients)

            with open('bad_pi.txt') as tf:
                msg.attach(MIMEText(tf.read(), 'plain'))
            with open('bad_pi.html') as hf:
                msg.attach(MIMEText(hf.read(), 'html'))

        elif condition == 'summary':
            msg['Subject'] = 'Pi Summary: ' + str(len(self.not_running)) + " not running"
            msg['From'] = self.username
            msg['To'] = ", ".join(self.recipients)

            with open('summary.txt') as tf:
                msg.attach(MIMEText(tf.read(), 'plain'))
            with open('summary.html') as hf:
                msg.attach(MIMEText(hf.read(), 'html'))

        # set up server
        server = smtplib.SMTP('smtp.gmail.com', 587)     # host address and port number of the particular email service provider
        server.starttls()
        server.login(self.username, self.password)

        # send the message
        server.send_message(msg)
        server.quit()
        print('SENT EMAIL')


    def _authenticateGoogleSpreadSheets(self):
        print("AUTHENTICATING")
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentialSpreadsheet, scope)

        for i in range(0,3): # Try to autheticate three times before failing
            print(i)
            try:
                gs = gspread.authorize(credentials)
            except:
                continue
            try:
                print("SELF.CONTROLLERGS")
                self.controllerGS = gs.open('Controller')
                pi_ws = self.controllerGS.worksheet('RaspberryPi')
            except:
                continue
            try:
                alldata = pi_ws.get_all_values()  # gives list of lists of rows
                # self.alldata_noheader = alldata[1:]
                # self.headers = pi_ws.row_values(1)
                return True
            except:
                continue
        return False

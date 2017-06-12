from email.MIMEBase import MIMEBase

def attachCSV(mimemultipart,csvdata,filename):
    part = MIMEBase('text', "csv")
    part.add_header(
        'Content-Disposition', 'attachment; filename="{}.csv"'.format(filename))
    part.set_payload(csvdata)
    mimemultipart.attach(part)



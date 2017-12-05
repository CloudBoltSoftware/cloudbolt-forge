from common.methods import set_progress
from utilities.models import ConnectionInfo
from xml.etree import ElementTree
from utilities import mail
from lxml import objectify
import time
# qualysapi python module must be intalled on the Cloudbolt server
# https://github.com/paragbaxi/qualysapi
import qualysapi
import os

# Each Environment needs a qualys_scanner perameter set with the appropriate onsite scanner name

# A .qcrc file must be created on the Cloudbolt server, in root's home directory for this job to function.
# The .qcrc should be owned by root and permissions of 0600
# Contents should be (see qualysapi documentation for details):
# [info]
# username = <Qualys User name>
# password = <Qualys password>
def generate_options_for_Scan_Type(server=None, **kwargs):
    # This provides the user 2 types of Scans to choose from
    # The values are the template id's for Report Templates.  These need to be changed for your environment
    options = [
            ('1921131', 'Project Production Readiness - Severities 3 thru 5'),
            ('2230696', 'General Inquiry - Severities 1 thru 5')
            ]
    return options

def generate_options_for_Report_Type(server=None, **kwargs):
    # This provides the user 4 types of report formats to choose from
    # The only Qualys API supported formats are pdf, csv, html, mht, and xml.
    # xml is not listed below because it does not support creating an xml report
    # base on multiple scans.
    #
    # HTML and MHT are commented out because they are treated as Malware by our 
    # email
    options = [
            ('pdf', 'PDF'),
            # ('html', 'HTML'),
            # ('mht', 'MHT'),
            ('csv', 'CSV')
            ]
    return options

def run(job, logger, **kwargs):
  
    start = time.time()
    state = 'success'
    scan_type = '{{Scan_Type}}'
    template_id = scan_type
    report_type = '{{Report_Type}}'
    requestor_email = job.owner.user.email
    # Allow the user to have the PDF or CSV report sent to additional email addresses
    cc_list = '{{Email_List}}'
    # Allow the user to add custom text to the bottom of the email
    extra_body = '{{Email_Extra_Body}}'
    # Verify Cloudbolt know the email address of the requestor
    if requestor_email is None or requestor_email == '': return "FAILURE", "Please update your email in your user profile.", ""
    server = job.server_set.first()
    job_id = job.id
    session = qualysapi.connect()
    # Determine the TYPE of the Report Template
    # If TYPE is 'Manual', assume it is "Scan Based"
    # If TYPE is "Auto", assume it is "Host Based"
    template_list = session.request('report_template_list.php')
    templates = objectify.fromstring(template_list)
    template_type = ''
    for template in templates.REPORT_TEMPLATE:
        if str(template.ID) == scan_type:
            template_type = template.TYPE
    if template_type == '': return "FAILURE", "Unable to locate Report Template with ID " + scan_type, ""
    call = 'scan.php'
    ipaddr = ''
    error_code = ''
    # Build an array to capture a dictionary of Qualys Scanner, Server names and IPs
    # And Build and array of the scanners
    svr_info = []
    scanner_list = []
    for server in job.server_set.all():
        if str(server.status) == 'ACTIVE':
            svrinfo = {'scanner': str(server.environment.qualys_scanner), 'ipaddress': str(server.ip), 'name': str(server)}
            svr_info.append(svrinfo)
            scanner_list.append(str(server.environment.qualys_scanner))

    # Find the unique scanners
    sum_vuls = 0
    sev1 = 0
    sev2 = 0
    sev3 = 0
    sev4 = 0
    sev5 = 0
    scans = ''
    svr_string = ''
    scanners = set(scanner_list)
    for scanner in scanners:
        # build the list of IPs for this scanner
        ipaddr = ''
        for svr in svr_info:
            if svr['scanner'] == scanner:
                svr_string = svr_string + svr['name'] + ' : ' + svr['ipaddress'] + '\n'
                if ipaddr == '':
                    ipaddr = svr['ipaddress']
                else:
                    ipaddr = ipaddr + ',' + svr['ipaddress']

        parameters = {'scan_title': 'Scan of ' + str(ipaddr) + ': Initiated via Cloudbolt job ' + str(job.id) + ' on Scanner ' + scanner, 'iscanner_name': scanner, 'ip': str(ipaddr), 'option': "!IHG - Internal - Authenticated Scan - Full TCP", 'save_report': 'yes'}
        logger.debug('Request parameters: ' + str(parameters))
        set_progress("- Running Qualys Scan from " + scanner + "...")
        xml_output = session.request(call, parameters, concurrent_scans_retries=2, concurrent_scans_retry_delay=300)
        root = objectify.fromstring(xml_output)
        if hasattr(root, 'IP'):
            logger.debug('Root Attrib: ' + str(root.attrib))
            if scans == '':
                scans = str(root.attrib['value'])
            else:
                scans = scans + ',' + str(root.attrib['value'])
        else:
            logger.debug('Error Code: ' + str(root.ERROR.attrib['number']))
            state = 'fail'
            error_code = root.ERROR.attrib['number']
            if state == 'success':
                return "SUCCESS", "Qualys Scan successfully completed. Check your email for PDF/CSV reports", ""
            elif state == 'warning':
                return "WARNING", "Qualys Scan found vulneribilities", ""
            else:
                if error_code == '3007':
                    return "FAILURE", "Too many concurrent scans running at this time. Please try again later.", ""
                elif error_code == '3003':
                    return "FAILURE", "Not Allowed to scan these IPs.", ""
                else:
                    logger.debug('xml return from Qualys: ' + xml_output)
                    return "FAILURE", "Qualys Scan request failed with unknown error", ""

    logger.debug('template_id: ' + template_id)
    logger.debug('job.id: ' + str(job.id))
    logger.debug('report_type: ' + report_type)
    logger.debug('scans: ' + str(scans))
    if template_type == 'Auto':
        gen_pdf_report = session.request('/api/2.0/fo/report', {'action': 'launch', 'template_id' : template_id, 'report_title': 'Cloudbolt report for job ' + str(job.id), 'report_type': 'Scan', 'output_format': report_type, 'report_refs': scans, 'ips': str(ipaddr)})
    else:
        gen_pdf_report = session.request('/api/2.0/fo/report', {'action': 'launch', 'template_id' : template_id, 'report_title': 'Cloudbolt report for job ' + str(job.id), 'report_type': 'Scan', 'output_format': report_type, 'report_refs': scans})

    gen_pdf = objectify.fromstring(gen_pdf_report)
    pdf_report_id = gen_pdf.RESPONSE.ITEM_LIST.ITEM['VALUE']

    scan_array = scans.split(',')
    total_vuls = 0
    for xml_scan in scan_array:
        if template_type == 'Auto':
            gen_xml_report = session.request('/api/2.0/fo/report', {'action': 'launch', 'template_id' : template_id, 'report_title': 'Cloudbolt report for job ' + str(job.id), 'report_type': 'Scan', 'output_format': 'xml', 'report_refs': xml_scan, 'ips': str(ipaddr)})
        else:
            gen_xml_report = session.request('/api/2.0/fo/report', {'action': 'launch', 'template_id' : template_id, 'report_title': 'Cloudbolt report for job ' + str(job.id), 'report_type': 'Scan', 'output_format': 'xml', 'report_refs': xml_scan})
        gen_xml = objectify.fromstring(gen_xml_report)
        xml_report_id = gen_xml.RESPONSE.ITEM_LIST.ITEM['VALUE']

        logger.debug('Waiting for XML Report to be Generated')
        retries = 40
        sleepseconds = 15
        count = 1
        while count <= retries:
            time.sleep(sleepseconds)
            xml_status_request = session.request('/api/2.0/fo/report', {'action': 'list', 'id': xml_report_id})
            xml_status = objectify.fromstring(xml_status_request)
            logger.debug(xml_status)
            if hasattr(xml_status.RESPONSE, 'REPORT_LIST') and xml_status.RESPONSE.REPORT_LIST[0].REPORT.STATUS['STATE'] == 'Finished':
                count = retries * 2 + 10
            count += 1
        xml_report = session.request('/api/2.0/fo/report', {'action': 'fetch', 'id': xml_report_id})

        report = objectify.fromstring(xml_report)
        if hasattr(report, 'IP'):
            logger.debug('report Attrib: ' + str(report.attrib))
            for svrip in report.IP:
                svrname = svrip.attrib['name']
                if hasattr(svrip, 'VULNS'):
                    for x in svrip.VULNS.CAT:
                        sum_vuls += len(x.VULN)
                        for vul in x.VULN:
                            set_progress('Server: ' + svrname + ' , Severity: ' + vul.attrib['severity'] + ' , QID: ' + vul.attrib['number'] + ' , VULNERBILITY: ' + vul.TITLE)
                            if vul.attrib['severity'] == '1' : sev1 += 1
                            if vul.attrib['severity'] == '2' : sev2 += 1
                            if vul.attrib['severity'] == '3' : sev3 += 1
                            if vul.attrib['severity'] == '4' : sev4 += 1
                            if vul.attrib['severity'] == '5' : sev5 += 1
                else:
                    logger.debug('NO Vulnerabilites found for ' + str(svrname))
        elif hasattr(report, 'HOST_LIST'):
            total_vuls = total_vuls + report.HEADER.RISK_SCORE_SUMMARY['TOTAL_VULNERABILITIES']

        del_xml = session.request('/api/2.0/fo/report', {'action': 'delete', 'id': xml_report_id})

    logger.debug('Waiting for ' + report_type + ' Report to be Generated')
    count = 1
    while count <= retries:
        time.sleep(sleepseconds)
        pdf_status_request = session.request('/api/2.0/fo/report', {'action': 'list', 'id': pdf_report_id})
        pdf_status = objectify.fromstring(pdf_status_request)
        if pdf_status.RESPONSE.REPORT_LIST[0].REPORT.STATUS['STATE'] == 'Finished':
            count = retries * 2 + 10
        count += 1

    pdf_report = session.request('/api/2.0/fo/report', {'action': 'fetch', 'id': pdf_report_id})
    filename = '/tmp/' + str(job.id) + '.' + report_type
    with open(filename, 'wb') as f:
        f.write(pdf_report)
    f.close
    subject = 'Qualys Report for Cloudbolt job ' + str(job.id)
              
    if extra_body and extra_body != '':
        body = subject + '\n\nScanned Servers\n' + svr_string + extra_body
    else:
        body = subject + '\n\nScanned Servers\n' + svr_string
    sender = requestor_email
    recipient = [requestor_email]
    if cc_list and cc_list != '':
        ccs = cc_list.split(',')
        recipient.extend(ccs)
    attach = [(filename, 'application/' + report_type)]
    mail.send_mail(subject, body, sender, recipient, attachments=attach, filter_recipients=False)
    os.remove(filename)

    sum_3_5 = sev3 + sev4 + sev5
    sum_1_2 = sev1 + sev2
    if template_type == 'Auto':
        set_progress(str(total_vuls) + ' Critical Vunerabilites Found. See emailed report for details')
        if total_vuls > 0: state = 'warning'
    else:
        set_progress(str(sum_3_5) + ' Critical Vunerabilites Found. Sev 5: ' + str(sev5) + ', Sev 4: ' + str(sev4) + ', Sev 3: ' + str(sev3))
        if sum_1_2 > 0: set_progress(str(sum_1_2) + ' Non-Critical Vunerabilites Found.  Sev 2: ' + str(sev2) + ', Sev 1: ' + str(sev1))
        if sum_3_5 > 0: state = 'warning'

    done = time.time()
    restoreduration = "%.2f" % (done - start)
    # logger.debug("Qualys Scan duration(secs): " + restoreduration)

    if state == 'success':
        logger.debug("[SUCCESS] Qualys Scan duration(secs): " + restoreduration)
        return "SUCCESS", "Qualys Scan successfully completed. Check your email for PDF/CSV reports", ""
    elif state == 'warning':
        logger.debug("[WARNING] Qualys Scan duration(secs): " + restoreduration)
        return "WARNING", "Qualys Scan found vulneribilities", ""
    else:
        if error_code == '3007':
            logger.debug("[FAILURE] Qualys Scan duration(secs): " + restoreduration)
            return "FAILURE", "Too many concurrent scans running at this time. Please try again later.", ""
        elif error_code == '3003':
            logger.debug("[FAILURE] Qualys Scan duration(secs): " + restoreduration)
            return "FAILURE", "Not Allowed to scan these IPs.", ""
        else:
            logger.debug("[FAILURE] Qualys Scan duration(secs): " + restoreduration)
            logger.debug('xml return from Qualys: ' + xml_output)
            return "FAILURE", "Qualys Scan request failed with unknown error", ""

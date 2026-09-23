The data set contains the following files with the corresponding descriptions. It is recommended to review the files in the order they are presented below. 

Setup and Testplan.txt - This file documents the overall logistics and test plan execution. NOTE - UR Scripts V5 and PLC 1.4.3 reference robot script and PLC script, respectively, that are executed to generate the data in this set. 

RobotVid.mp4 - MP4 video file that shows a single part being cycled through the workcell. 

UseCaseTimeline.PDF - the activities, corresponding to 14 unique timestamps per part, are presented in this PDF. This document is critical to understanding the times presented in the PartData.csv file. 

PLC Data.zip - This file contains four data set .csv files that are all output from the PLC. The files:
- PartData.csv - UR robot times should be divided by 10^6 to convert to seconds; All other times are PLC times and should be divided by 10^ to convert to seconds; Reference the associated publications for details on the meaning of each field/value. 
- UR3Data.csv - PLC Times (divide by 10^7 to convert to seconds), Robot Times (divide by 10^6 to convert to seconds), actual joint positions of all 6 UR3 robot joints (radians), actual joint velocities of all 6 UR3 robot joints (radians/sec), Tool Center Position (meters) 
- UR5Data.csv - PLC Times (divide by 10^7 to convert to seconds), Robot Times (divide by 10^6 to convert to seconds), actual joint positions of all 6 UR3 robot joints (radians), actual joint velocities of all 6 UR5 robot joints (radians/sec), Tool Center Position (meters) 

UR3RTDE.csv - Real Time Exchange Data from the UR3 - refer to https://www.universal-robots.com/articles/ur/real-time-data-exchange-rtde-guide/ for details on each value captured

UR5RTDE.csv - Real Time Exchange Data from the UR5 - refer to https://www.universal-robots.com/articles/ur/real-time-data-exchange-rtde-guide/ for details on each value captured

It is recommended to review two specific publications that present the configuration of the test bed, describe the use, and present additional details on the data collection. These publications, in the order they should be reviewed are:

B.A. Weiss and A.S. Klinger, "Identification of Industrial Robot Arm Work Cell Use Cases and a Test Bed to Promote Monitoring, Diagnostic, and Prognostic Technologies"
https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=923755, 2017.

A.S. Klinger and B.A. Weiss, "ROBOTIC WORK CELL TEST BED TO SUPPORT MEASUREMENT SCIENCE FOR MONITORING, DIAGNOSTICS, AND PROGNOSTICS"
https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=924910, 2018. 

Additional information on the overall research effort that this data is a part can be found at https://www.nist.gov/el/enhancing-maintenance-strategies-manufacturing-operations

Disclaimer: Certain commercial entities, equipment, or materials may be identified or referenced in this data, or its supporting materials, in order to illustrate a point or concept. Such identification or reference is not intended to imply recommendation or endorsement by NIST; nor does it imply that the entities, materials, equipment or data are necessarily the best available for the purpose. The user assumes any and all risk arising from use of this dataset.

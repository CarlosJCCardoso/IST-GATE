# IST-GATE

In this project we developed a system (IST-GATE) which allows the deployment of
access control gates (such as the one in SCDEEC), control the opening of the gates,
authenticate and control users that want to enter the gates while also providing access to usage
statistics and lists to administrators.

The final system has two types of human users: administrators and regular.
Regular users have access to the system by using their smartphone when entering a gate. In the
smartphone, users will authenticate using the FENIX username and password and will be given a QRCode which the gate will read finally granting the user access to the computers room.
Administrators will define the available gates and will see the listings of the gates usage.

In this work we were able to
- Define the architecture of the systems (services, pages, gates)
- Define the set of resources to be made available by the various components
- Define the relevant information (attributes) of such resources to be stored in a
Database
- Define the interfaces (WEB and REST) to access such resources
- Implement simple prototypes (in python and Javascript) to replicate the behavior of a
real gate
- Implement a simple web server for access and management of resources

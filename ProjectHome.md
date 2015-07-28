# What is this project, in a few lines #
This project is about writing a flexible, intelligent and open source simulation engine for operational-level wargaming. Operational here means that the simulation is focusing on tactics used in the "last 1000 yards", which is the realm of non-commissioned officers (NCOs). To learn more about the innovative features and simulation philosophy, have a look at the [BasicPrinciple](BasicPrinciple.md) page.

The project has over 20K lines of code and is in development since 2006. It is moving slowly but steadily.

# What is an engine? #
This project does the simulation part of wargaming. It takes input as XML files (and other for maps), simulate and returns a new set of XML files. Interfacing with the user belongs to another project: probably a browser-based interface.

# Platform #
It is written in Python and aimed to run on Linux servers. There is no reason why the simulator would not run on other platforms, but cross-platformeness isn't a priority.
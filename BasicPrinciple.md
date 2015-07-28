# Time in the Sandbox #
The OPCON sandbox is a continuous time simulation which runs in batch mode. Events are put into a scheduler, and the simulation proceeds from event to event in chronological order. This means that the simulation behave as a turn-based simulation without the contraints of a using turn sequences nor pre-determined turn lenght.

# World in the Sandbox #
The world in the Sandbox is defined in two different ways. There is a raster layer, or map which can be created with any graphic editing package to overlay with an actual graphical maps. This layer encodes the terrain type from a designer's defined list of terrain types (an example is unrestricted, restricted, severely restricted, urban, open water). This is quite similar to the terrain encoding in Decisive Action. The most innovative world representation is the infrastructure layer, which is a network of locations, connected by routes. Each routes and nodes have properties and can contain "infrastructures", designer-defined fixed entity which can have a number of properties. A map designer provide a minimal infrastructure to model the road network as well as the location of important landmarks and built-up areas. To the map's network, a scenario designer can add one of more networks that are specific to a scenario.

The infrastructure layer is something that doesn't exist in any other wargames, it can be used to model very fine grained map areas, or put on the ground special buildings or installations with their own footprints and equipment.

# Units in the Sandbox #
Units are command units which are either human/AI controlled. In the same simulation, there can be any number of kind of entities that are modeled using different rules and procedures. The knowledge of a unit is limited by a number of factors, the most important is the unit's own bandwidth, or the maximum quantity of information that a unit can hold about its situation. A scenario designer may decide that managing information is an important aspect of a scenario, and compel the commanders to articulate their Critical Information Requirements (CIR) more clearly. Units also abide by a flexible logistics systems which has no limitations to the level of details that can be tracked, but at the same time doesn't require a scenario designer to define more details than needed for the game/training exercise. In other words, logistics can be modeled as precisely as required, and not a single bit more than that.

# Communication in the Sandbox #
All COMMS in the Sandbox are following US/NATO format. They are encoded, however in a manner that is readable for the AI and thus are structured in many places. However, humans gets to interact with HTML versions of the COMMS which are not that much distinguishable from the real deal.

# AI in the Sandbox #
The AI is staffwork oriented. It is very powerful, but geared to take care of the huge quantity of details that goes into implementing a commander's decision. The goal for the Sandbox's AI is to be able to implement any orders from a minimal set of instructions and control measures, and break it down into multi-phased operations to make it happen. If this works well, writing a command AI shouldn't be difficult, but this isn't an objective for the initial release of the project.

# Everything is in human-readable format #
Everything is represented with XML files. It can be manipulated by hand at any point in the design and umpiring process. The XML scheme relies on templates, which cuts down the definitions of units, models and infrastructures to a minimum.
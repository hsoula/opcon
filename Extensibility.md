# Introduction #

There are three main places where the project must be extensible. They are described here.


# Models #
Each unit is an entity which is a union of a state (data that changes from unit to another) and a number of Stateless models. The models are:
  * [logistics](logistics.md)
  * [combat](combat.md)
  * [movement](movement.md)
  * [C3](C3.md)
  * [intelligence](intelligence.md)

Each unit is defined by inheritable templates which contain a model or a template for a model for each of the modules. All of the data is stored in XML files, which can be edited by hand, or eventually with some kind of UI.

Refer to the ExtensibilityUsability page for some use case to eventually test.
# Code #

# Scenario design #
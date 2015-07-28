# Principle #
An entity is a collation of a few elements:
**Identification of the entity and the command echelon that it controls.** [State](State.md) data which is unit specific and changes over time.
**Models which are stateless, and act as controllers to resolve various aspect of the entities' actions.**

# Reading in an Entity from a Scenario definition #
An entity must be embedded in a 

&lt;OOB&gt;

 tag which itself is embedded in a 

&lt;side&gt;

 node. The bulk of the information for an entity can be templated.
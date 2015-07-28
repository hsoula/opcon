# Principle #
Units are made of components, which are either [personnel](personnel.md) or [vehicle](vehicle.md). These components have [sensors](sensors.md) and are generating [signatures](signatures.md). A given sensor has a chance of acquiring the signature with a probability that depends on the strength of the signature, the activities of the target unit and other atmospheric effects. Once a contact is acquired, each sensor can classify the target unit based on a list of information fields and associated probabilities of filling them up.

The collation of information fields is called a contact. As time goes by, contacts get updated with new information, can be sent as CNTREP, can be merged with other contact on the same units and passed back down the chain as part of an INTSUM/INTREP.

# Routine #
Lets assume that the detecting unit is called **ESEN** and the target unit is called **ETGT**. For each possible pair ESEN|ETGT, the following is done:

  1. Enumerate each sensor in ESEN as SENSOR
  1. Determine whether ETGT has a signature that SENSOR is sensitive to.
  1. If this is the case, determine whether the SENSOR's Area of Interest overlaps with the footprint of ETGT.
  1. If this is the case, determine the strength of the signature, modified by ETGT's activity and other environmental factors which the SENSOR is defined as either require, be degraded by or be enhanced by.
  1. If SENSOR acquires ETGT, cycle through SENSOR's list of information fields that can be classified (and their likelihood). Determine for each field if the classification is made.
  1. Update the newly classified fields into the existing contact, or create a new contact.

Depending on the SOP/OPORD, the contact may be reported to HIGHER.

# Parameterizing the intelligence model #
The only parameter to the intelligence mode is to create a list of signatures. The base definition for the intelligence model can be found [here](https://code.google.com/p/opcon/source/browse/trunk/Data/intelligence.xml). In the section below, this definition is documented:

## Default model ##
```
<intelligence template="base"/>
```
The default model draws from the base model, whether the template is specified or not. The base model is visible, has a thermal signature with properties similar to the visual signature (but works best in the dark/cold), and emit sound.

## Signatures ##
```
<intelligence template="base">
      <signature signal="visual" level="likely"/>
</intelligence>
```
In this simple example, all visual signature are likely to be acquired, regardless of the target unit's activity. The signal must be a single token (no whitespaces) which matches the label of a signal that at least one sensor is sensitive to.  The level field is one of the possible [TOEM](TOEM.md) labels:
  * very\_unlikely
  * unlikely
  * neutral
  * likely
  * very\_likely

```
<intelligence template="base">
      <signature signal="thermal" sameas="visual"/>
</intelligence>
```
In this example, the thermal signature behaves the same as the visual signature, except that the thermal sensors have a different sets of requirements and modifiers.

```
<intelligence template="base">
      <signature type="visual" level="likely">
          <very_likely>combat,transit</very_likely>
          <neutral>deployed,hasty defense</neutral>
          <unlikely>prepared defense</unlikely>
      </signature>
</intelligence>
```
The example above is a more elaborate sample where the stance and the activity of a unit affects its signature. If there are more than one label possible for a given signature level, use comma to delimit the elements.

In this case, the unit would likely be detected visually if in range and observed by a unit. However, this likelihood is much higher if the unit is either fighting or moving overland. It is also much more difficult to acquire a target unit if this unit is in prepared defence.
# Principle #
Sensors are device that pick up on one kind of signal and enable to collect information on a unit which gets collated as a [contact](contact.md).

A sensor can only acquire if the sensor unit and the target units meet the requirements. The probability of acquisition is degraded and enhanced by other factors which can be environmental in nature.


# Format definition #

```
<sensor name="visual" signature="visual">
      <!-- Requirements and degradation are labels that will be handled by the INTEL model -->
      <requires>LOS</requires>
      <requires>light</requires>
      <degraded_by>rain</degraded_by>
      <degraded_by>fog</degraded_by>
      <degraded_by>smoke</degraded_by>
      <degraded_by>terrain</degraded_by>

      <!-- Which type of information can be classified by this sensor -->
      <classify>
          <not_used>bearing,range</not_used>
          <very_unlikely>effectiveness,moral,fatigue,supply levels</very_unlikely>
          <unlikely>augmentation,identity</unlikely>
          <neutral>side,size,higher_formation,course,speed,activity</neutral>
          <likely>personel,vehicles,location,altitude,stance</likely>
          <very_likely>TOE</very_likely>
      </classify>
</sensor>
```

## Implemented Fields ##
  * TOE
  * side
  * size
  * higher\_formation
  * identity
  * augmentation
  * location
  * personel
  * vehicle
  * stance
  * activity
  * course
  * speed
  * range
  * bearing
  * altitude
  * casualty\_level
  * morale
  * fatigue
  * suppression
  * supply\_level
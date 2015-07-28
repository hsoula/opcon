# General Principle #
The logistics models is concerned with the tracking of materiel during a scenario. The materiel is stored in a custom data structure called the [supply\_package](supply_package.md). Units have the following properties:

Stateless properties
  1. capacity : a supply\_package that represent the maximal quantity of materiel that a unit can lift with its organic assets.
  1. Consumption\_rate : There are four consumption rates:
    1. idle : materiel expenditure in STON per hour when the unit/system does nothing.
    1. transit : materiel expenditure when the unit is relocating.
    1. combat : materiel expenditure when the unit/system if fighting.
    1. service : materiel expenditure when the unit/system is providing CSS.
  1. basic\_load: the number of hours for each consumption\_rate class that a unit will attempt to maintain through routine resupply requests.

State properties
  1. cargo : the quantity of materiel transported by the unit's organic assets.
  1. mounted dismounts: The number of personel lifted for ferry or relocation ops. Doesn't include the crew of the vehicle itself.

# XML examples #
The basic definition. It has no capacity for materiel nor passenger lift. It has no crew. By default, all logistic models inherit 72 hours of **idle** activity supply, 6 for **transit** and 1 hour of intense **combat**. The basicload property is meaningless in the base example. Finally, the base model doesn't expand any supply, regardless of the unit's activity. Essentially, a unit using this model will operate with the logistic model **turned off**.
```
<logistics name="base">
   <capacity type="LOGPAC"/>
   <passenger_lift>0</passenger_lift>
   <crew>0</crew>
   <basicload>
       <idle>72.0</idle>
       <transit>6.0</transit>
       <combat>1.0</combat>
   </basicload>
   <consumption_rate>
       <idle class="LOGPAC"/>
       <transit class="LOGPAC"/>
       <combat class="LOGPAC"/>
       <service class="LOGPAC"/>
   </consumption_rate>
</logistics>
```

## capacity ##
The quantity of material that a unit can carry. If this field is omitted or left blank, the capacity will be set to the unit's cargo with a full basic load (as defined when the unit is created).

## passenger\_lift ##
The number of individuals that can be carried by the entity.

## crew ##
The number of individuals that are required to operate the entity (vehicle) and are not disembarking when a dismount order is given.

## basicload ##
The number of hours of average consumption for each of the consumption rates.

## consumption\_rate ##
Expressed in supply\_package in kg per unit of time (hour by default). This supply is expended only when the unit is performing this type of activity.
# General Principle #
The supply\_package is a Python dictionary which provides a limited form of taxonomy for materiel. By default, the supply is assumed to be **Unspecified**, which means that it can be anything up to the quantity specified. However, supply can be specified in generic supply classes or even further specified into a specific type of item.

Here are some examples:
  * Unspecified -- _Anything_
  * III -- _class III supply: POL and lubricants_
  * III(AVGAS) -- _Fuel for aircrafts_
  * V -- _Generic ammunition supply_
  * V(155mmSMOKE) -- _SMOKE shells for 155mm ARTY_
  * water -- _as the name implies_


# Minimal Abstraction #
This hiearchic system is designed to minimize the quantity of unnecessary details. A scenario designer should determine whether it matters to the commander whether a certain type of supply is limiting and keep track only of these while leaving the rest as Unspecified.

For example, if a scenario depends a lot on the number of Javelin missiles, the FSB's store could be made to contain a certain quantity of **Unspecified** materiel and a given quantity of **V(JAVELIN-ATGM)**. All supply requests from units will be drawn from the Unspecified source except for the requests for V(JAVELIN-ATGM). When the store of Javelins are empty, the supply requests can no longer be filled. However, if the FSB has a specified quantity of class V supply but no V(JAVELIN-ATGM), requests for Javelin missiles will be drawn from the class V store, but never from the Unspecified stores.

Database editors are better to fully define the consumption rates of their new vehicle/personel type and leave to the scenario designer the option to care about tracking specific types of supply.

# XML encoding #
The XML encoding of a supply\_package is done my specifying the type of a node as **LOGPAC**. Optional properties to a node are the following:

  * units : The unit to use. By default, the STON (short ton), but can be any of the following: STON, kg, lt, gal, lb .
  * time\_units : If the LOGPAC expresses a rate, this field specify the unit of time for this rate. By default it is in hours, but can be any of the following: min, hr, day.
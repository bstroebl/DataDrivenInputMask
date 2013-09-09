Usage
============
 
The plugin adds a submenu in the plugins menu. The entry *Initialize Layer*
(re)initializes the active layer in the project with the DataDrivenInputMask.

Accessing the mask
---------------------

* The initialization adds an action to the layer. With this action the mask can be accessed by simply clicking on a feature.
* If a feature is selected, the submenu's entry *Show Input Form* is another way to open the mask.

Using the search
---------------------

Show Search Form offers the same mask for searching features into the active layer.

Customizing
---------------------

To make your own custom masks either pass appropriate parameters to DdManager’s initLayer or subclass ddui.DataDrivenUi.


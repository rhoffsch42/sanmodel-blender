# sanmodel-blender
A Blender addon to import/export sanmodel files. This is a Work In Progress 

## Install
Copy sanmodel_importer.py in the Blender addons folder, it should be located here:
`C:\Users\<user_name>\AppData\Roaming\Blender Foundation\Blender\3.0\scripts\addons`
Then, reload scripts in Blender.

## How to use
The sanmodel panel is located under the usual panels Item, Tool and View. For now, it is recommanded to open the System Console as almost all errors will be prompted here (Window > Toggle System Console).

### import panel
You can simply import a sanmodel with the button.
After the import, its properties will be displayed, but the model is not yet created. To create it, just click the button "Create new object". Depending on the size of the original model, it might be too small or too big, you can adjust the scale on blender. 

### export panel
Warning: armature not supported yet, you can only export a basic object, make sure you correclty selected it before the export.
Before exporting, you can write a name in the text field for the model, this name will be used in the data, this is not the name of the exported file.


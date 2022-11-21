# sanmodel-blender
A Blender addon to import/export sanmodel files. This is a Work In Progress. 

## Install
1. Download sanctuary-model-import-export.zip
2. On Blender: Edit > Preferences > Add-ons : click the button "Install..." and select the downloaded file. The add-on will appear on the list, its name is "Sanctuary model importer/exporter", make sure it is enabled by checking its box.
3. The add-on should be installed and loaded, but you can force a reload if needed: click on the Blender logo > System > Reload Scripts.

## How to use
The sanmodel panel is located under the usual panels Item, Tool and View, they're located on the top right of the main viewport, if you dont find them, there should be a little arrow pointing left on the border, click it.  For now, it is recommanded to open the System Console as almost all errors will be prompted here (Window > Toggle System Console).

### Import panel
You can simply import a sanmodel with the button.
After the import, its properties will be displayed, but the model is not yet created. To create it, just click the button "Create new object". Depending on the size of the original model, it might be too small or too big, you can adjust the scale on blender. 

### Export panel
Armature should work, but YZ axis might be swapped, it is still worked on at the moment.
Before exporting, you can write a name for the model in the text field, this name will be used in the data, this is not the name of the exported file. To export, select an object and click the export button.

### Settings panel
Blender, Unity, or other 3d engines, dont use the same coordinate system. These settings act on the coordinates (vertices and UV) when importing/exporting. There might be some tweeking to do, feedbacks are welcome.

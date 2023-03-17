import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pac_app/config.dart';
import 'package:pac_app/pages/info_page.dart';
import 'package:pac_app/pages/cropper_page.dart';

class HomePage extends StatefulWidget {
  final CameraController controller;

  const HomePage({super.key, required this.controller});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {

  // sincronizado com: FlashMode.values = [off, auto, always, torch]
  final _flashIcons = <Icon>[
    const Icon(Icons.flash_off), // não usar flash
    const Icon(Icons.flash_auto), // modo automático
    const Icon(Icons.flash_on), // usar flash quando tirar a foto
    const Icon(Icons.flare_sharp) // manter flash ligado
  ];

  var _flashModeIndex = 0; // iniciar com FlashMode.off
  var _isLoading = false;

  @override
  Widget build(BuildContext context) {

    final screenSize = MediaQuery.of(context).size;
    /*widget.controller.setFocusPoint(Offset(
      _center.dx / screenSize.width,
      _center.dy / (screenSize.width * widget.controller.value.aspectRatio)
    ));
    widget.controller.setFocusMode(FocusMode.locked);*/

    widget.controller.setFlashMode(FlashMode.values[_flashModeIndex]);

    final _targetScaller = screenSize.width/(Default.getResolutionSize()?.width ?? 1);
    final pelletField = Target(
      width: Default.imageWidth*_targetScaller,
      height: Default.imageHeight*_targetScaller
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pellet Area Calculator'),
      ),
      body: Center(child: 
        _isLoading ? const CircularProgressIndicator() :
        CameraPreview(
          widget.controller,
          child: pelletField
        )
      ),
      floatingActionButton: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: <Widget>[
          FloatingActionButton(
            backgroundColor: Colors.transparent,
            onPressed: () => setState((){
                _flashModeIndex = (_flashModeIndex + 1) % FlashMode.values.length;
                widget.controller.setFlashMode(FlashMode.values[_flashModeIndex]);
            }),
            heroTag: 'flash',
            child: _flashIcons[_flashModeIndex],
          ),
          FloatingActionButton(
            backgroundColor: Colors.white,
            foregroundColor: Colors.grey,
            onPressed: () async {
              late XFile imageXFile;
              try{
                setState((){
                  _isLoading = true;
                });
                imageXFile = await widget.controller.takePicture();
                await regularizeImage(
                  imageXFile.path,
                  width: Default.imageWidth * pelletField.scaleFactor,
                  height: Default.imageHeight * pelletField.scaleFactor
                );
              } catch (e) {
                debugPrint(e.toString());
              } finally {
                setState((){
                  _isLoading = false;
                });
                widget.controller.resumePreview();
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => InfoPage(imagePath: imageXFile.path))
                );
              }
            },
            heroTag: 'camera',
            child: const Icon(Icons.camera_alt_outlined)
          ),
          FloatingActionButton(
            backgroundColor: Colors.transparent,
            onPressed: () async {
              widget.controller.resumePreview();
              ImagePicker().pickImage(
                source: ImageSource.gallery
                ).then((imageXFile) {
                  if (imageXFile != null){
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => Cropper(imageXFile: imageXFile))
                    );
                  }
                }
              );
            },
            heroTag: 'gellery',
            child: const Icon(Icons.photo),
          ),
        ]
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.miniCenterFloat,
      backgroundColor: Colors.transparent,
    );
  }
}
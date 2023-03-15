import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:pac_app/config.dart';
import 'package:pac_app/pages/info_page.dart';
import 'dart:io' show Platform;

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

  var isLoading = false;

  @override
  Widget build(BuildContext context) {

    final size = MediaQuery.of(context).size;
    /*widget.controller.setFocusPoint(Offset(
      _center.dx / size.width,
      _center.dy / (size.width * widget.controller.value.aspectRatio)
    ));
    widget.controller.setFocusMode(FocusMode.locked);*/

    widget.controller.setFlashMode(FlashMode.values[_flashModeIndex]);

    final alpha = size.width/(getResolutionSize()?.width ?? 1);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pellet Area Calculator')),
      body: Center(child: 
        isLoading ?
        const CircularProgressIndicator() :
        CameraPreview(
          widget.controller,
          child: Center(child: Container(
              width: getImageWidth()*alpha,
              height: getImageHeight()*alpha,
              decoration: BoxDecoration(
                  shape: BoxShape.rectangle, 
                  border: Border.all(color: Colors.red, width: 3)
                ),
              child: const Center(child: Icon(Icons.add, color: Colors.red)),
            )
          )
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
              late XFile imageFile;
              try{
                setState((){
                  isLoading = true;
                });
                imageFile = await widget.controller.takePicture();
                await regularizeImage(imageFile.path);
              } catch (e) {
                debugPrint(e.toString());
              } finally {
                setState((){
                  isLoading = false;
                });
                widget.controller.resumePreview();
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => InfoPage(imagePath: imageFile.path))
                );
              }
            },
            heroTag: 'camera',
            child: const Icon(Icons.camera_alt_outlined)
          ),
          FloatingActionButton(
            backgroundColor: Colors.transparent,
            onPressed: (){},
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
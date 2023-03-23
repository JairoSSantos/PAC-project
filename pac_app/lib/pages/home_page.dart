import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pac_app/config.dart';
import 'package:pac_app/pages/info_page.dart';
import 'package:image_cropper/image_cropper.dart';

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

  late int _flashModeIndex;
  late bool _isLoading;
  late double _baseScaleZoom;
  late double _scaleZoom;
  var _maxScaleZoom = 1.0;

  @override
  void initState(){
    super.initState();
    _flashModeIndex = 0; // iniciar com FlashMode.off
    _isLoading = false;
    widget.controller.getMinZoomLevel().then(
      (value) {
        _baseScaleZoom = _scaleZoom = value;
      }
    );
    widget.controller.getMaxZoomLevel().then(
      (value){
        _maxScaleZoom = value;
      }
    );
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp
    ]);
  }

  void setLoading({bool? value}) => setState((){
    _isLoading = value ?? !_isLoading;
  });

  void updateFlashMode() => setState((){
      _flashModeIndex = (_flashModeIndex + 1) % FlashMode.values.length;
      widget.controller.setFlashMode(FlashMode.values[_flashModeIndex]);
  });

  void takePicture(BuildContext context, {required double width, required double height}) {
    widget.controller.takePicture().then(
      (XFile imageXFile) {
        setLoading(value: true);
        widget.controller.pausePreview();
        Regularizer(imagePath: imageXFile.path)
          ..crop(width: width, height: height)
          ..resize()
          ..save();
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => InfoPage(
              imagePath: imageXFile.path
            )
          )
        ).whenComplete(() {
          widget.controller.resumePreview();
          setLoading(value: false);
        });
      },
      onError: (error) => showDialog(
        context: context, 
        builder: (context) => AlertDialog(
          title: const Text('Erro ao tirar foto!'),
          content: Text(error.toString())
        )
      )
    );
  }

  void pickImage(BuildContext context){
    widget.controller.pausePreview();
    ImagePicker().pickImage(
      source: ImageSource.gallery
    ).then((XFile? imageXFile) {
      if (imageXFile != null){
        ImageCropper().cropImage(
          sourcePath: imageXFile.path,
          aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
        ).then((CroppedFile? croppedFile) {
          if (croppedFile != null){
            Regularizer(imagePath: croppedFile.path)
              ..resize()
              ..save();
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => InfoPage(
                  imagePath: croppedFile.path
                )
              )
            );
          }
        });
      }
    }).whenComplete(
      () => widget.controller.resumePreview()
    );
  }

  @override
  Widget build(BuildContext context) {

    final screenSize = MediaQuery.of(context).size;
    widget.controller.setFocusPoint(const Offset(0.5, 0.5));
    widget.controller.setFlashMode(FlashMode.values[_flashModeIndex]);

    final targetScaller = screenSize.width/(Default.getResolutionSize()?.width ?? 1);
    final target = Target(
      width: Default.imageWidth*targetScaller,
      height: Default.imageHeight*targetScaller
    );

    return Scaffold(
      appBar: AppBar(title: const Text('Pellet Area Calculator')),
      backgroundColor: Colors.grey[400],
      body: Center(
        child: _isLoading ? 
        const CircularProgressIndicator() :
        GestureDetector(
          child: CameraPreview(
            widget.controller,
            child: target
          ),
          onScaleStart: (details) {
            _baseScaleZoom = _scaleZoom;
          },
          onScaleUpdate: (details) {
            _scaleZoom = (_baseScaleZoom * details.scale).clamp(1, _maxScaleZoom);
            widget.controller.setZoomLevel(_scaleZoom);
          }
        ),
      ),
      floatingActionButton: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: <Widget>[
          FloatingActionButton(
            backgroundColor: Colors.white,
            foregroundColor: Colors.blue,
            onPressed: () => updateFlashMode(),
            heroTag: 'flash',
            child: _flashIcons[_flashModeIndex],
          ),
          FloatingActionButton(
            backgroundColor: Colors.deepOrange,
            foregroundColor: Colors.white,
            onPressed: () => takePicture(
                context,
                width: Default.imageWidth * target.scaleFactor, 
                height: Default.imageHeight * target.scaleFactor
            ),
            heroTag: 'camera',
            child: const Icon(Icons.camera_alt)
          ),
          FloatingActionButton(
            backgroundColor: Colors.white,
            foregroundColor: Colors.blue,
            onPressed: () => pickImage(context),
            heroTag: 'gellery',
            child: const Icon(Icons.photo),
          ),
        ]
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.miniCenterFloat,
    );
  }
}
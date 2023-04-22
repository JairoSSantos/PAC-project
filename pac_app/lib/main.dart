import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter/services.dart';
import 'package:image_cropper/image_cropper.dart';
import 'package:pac_app/info_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  availableCameras().then(
    (cameras) => runApp(MaterialApp(home: App(camera: cameras.first)))
  );
}

class App extends StatefulWidget {
  final CameraDescription camera;

  const App({super.key, required this.camera});

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {
  late CameraController controller;

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

  void showErrorMessage(BuildContext context, String title, String message){
    showDialog(
      context: context, 
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context), 
            child: const Text('Ok')
          )
        ]
      )
    );
  }

  void setLoading(bool value) => setState((){
    _isLoading = value;
  });

  void updateFlashMode() => setState((){
      _flashModeIndex = (_flashModeIndex + 1) % FlashMode.values.length;
      controller.setFlashMode(FlashMode.values[_flashModeIndex]);
  });

  Future<String?> takePicture() async {
    XFile imageXFile = await controller.takePicture();
    setLoading(true);
    await controller.pausePreview();
    CroppedFile? croppedFile = await ImageCropper().cropImage(
      sourcePath: imageXFile.path,
      aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
    );
    return croppedFile?.path;
  }

  Future<String?> pickImage() async {
    setLoading(true);
    controller.pausePreview();
    XFile? imageXFile = await ImagePicker().pickImage(source: ImageSource.gallery);
    String? imagePath;
    if (imageXFile != null){
      CroppedFile? croppedImage = await ImageCropper().cropImage(
        sourcePath: imageXFile.path,
        aspectRatio: const CropAspectRatio(ratioX: 1, ratioY: 1)
      );
      imagePath = croppedImage?.path;
    }
    return imagePath;
  }

  Future<void> pushInfoPage(BuildContext context, String? imagePath) async {
    /*
    Este procedimento será chamado após cropImage,
    sendo necessário, portanto, verificar se o usuário 
    aceitou proseguir para InfoPage `assert (imagePath is String)`
    ou se o usuário decidiu retornar à câmera `assert (imagePath == null)`.
    */
    if (imagePath != null){
      await Navigator.push(
        context,
        MaterialPageRoute(builder: (context) => InfoPage(imagePath: imagePath))
      );
    }
    controller.resumePreview();
    setLoading(false);
  }

  @override
  void initState() {
    super.initState();
    _flashModeIndex = 0; // iniciar com FlashMode.off
    _isLoading = true;
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp
    ]);

    controller = CameraController(widget.camera, ResolutionPreset.max, enableAudio: false);
    controller.initialize().then(
      (_) {
        controller.getMinZoomLevel().then((value) {_baseScaleZoom = _scaleZoom = value;});
        controller.getMaxZoomLevel().then((value) {_maxScaleZoom = value;});
        controller.setFocusPoint(const Offset(0.5, 0.5));
        controller.setFlashMode(FlashMode.values[_flashModeIndex]);
        setLoading(false);
      },
      onError: (error) => debugPrint(error.toString())
    );
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pellet Area Calculator')),
      backgroundColor: Colors.white,
      body: Center(
        child: (_isLoading || !controller.value.isInitialized) ? 
        const CircularProgressIndicator() :
        GestureDetector(
          child: CameraPreview(controller),
          onScaleStart: (details) {_baseScaleZoom = _scaleZoom;},
          onScaleUpdate: (details) {
            _scaleZoom = (_baseScaleZoom * details.scale).clamp(1, _maxScaleZoom);
            controller.setZoomLevel(_scaleZoom);
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
            onPressed: () => takePicture().then(
              (path) => pushInfoPage(context, path),
              onError: (error) => showErrorMessage(context, 'Erro ao tirar foto!', error.toString())
            ),
            heroTag: 'camera',
            child: const Icon(Icons.camera_alt)
          ),
          FloatingActionButton(
            backgroundColor: Colors.white,
            foregroundColor: Colors.blue,
            onPressed: () => pickImage().then(
              (path) => pushInfoPage(context, path),
              onError: (error) => showErrorMessage(context, 'Erro ao escolher imagem!', error.toString())
            ),
            heroTag: 'gellery',
            child: const Icon(Icons.photo),
          ),
        ]
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.miniCenterFloat,
    );
  }
}
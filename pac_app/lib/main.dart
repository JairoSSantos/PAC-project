import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:pac_app/pages/home_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final cameras = await availableCameras();

  runApp(App(camera: cameras.first));
}

class App extends StatefulWidget {
  final CameraDescription camera;

  const App({super.key, required this.camera});

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {
  late CameraController controller;

  @override
  void initState() {
    super.initState();
    controller = CameraController(widget.camera, ResolutionPreset.max, enableAudio: false);
    controller.initialize().then((_) {
      if (!mounted) {
        return;
      }
      setState(() {});
    }).catchError((Object e) {
      if (e is CameraException) {
        switch (e.code) {
          case 'CameraAccessDenied':
            // Handle access errors here.
            break;
          default:
            // Handle other errors here.
            break;
        }
      }
    });
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!controller.value.isInitialized) {
      return Container();
    } else {
      return MaterialApp(
        home: HomePage(controller: controller)
      );
    }
  }
}
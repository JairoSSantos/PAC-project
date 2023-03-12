import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:pac_app/pages/info_page.dart';

const double _imageWidth = 256;
const double _imageHeight = 256;

class HomePage extends StatefulWidget {
  final CameraController controller;

  const HomePage({super.key, required this.controller});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool showFocusCircle = false;
  double x = 0;
  double y = 0;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return CameraPreview(widget.controller, // Camera
      child: GestureDetector( // Detector de toque
        onTapUp: (details) => _onTap(details),
        child: Stack(
          children: <Widget>[
            Positioned.fromRect(
              rect: Rect.fromCenter(
                center: Offset(size.width/2, size.height/2), 
                width: _imageWidth, 
                height: _imageHeight
              ), 
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.rectangle, 
                  border: Border.all(color: Colors.red, width: 3)
                ),
              )
            ),
            if (showFocusCircle) Positioned.fromRect(
              rect: Rect.fromCenter(center: Offset(x, y), width: 40, height: 40),
              child: Container(
                  decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 1.5)
                )
              )
            ),
            Scaffold(
              appBar: AppBar(title: const Text('Pellet Area Calculator')),
              floatingActionButton: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: <Widget>[
                  const Spacer(flex:3),
                  FloatingActionButton(
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.grey,
                    onPressed: () {
                      widget.controller.resumePreview();
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => const InfoPage())
                      );
                    },
                    heroTag: 'camera',
                    child: const Icon(Icons.camera_alt_outlined)
                  ),
                  const Spacer(flex:1),
                  FloatingActionButton(
                    backgroundColor: Colors.transparent,
                    onPressed: (){},
                    heroTag: 'gellery',
                    child: const Icon(Icons.photo),
                  ),
                  const Spacer(flex:1)
                ]
              ),
              floatingActionButtonLocation: FloatingActionButtonLocation.miniCenterFloat,
              backgroundColor: Colors.transparent,
            )
          ]
        )
      )
    );
  }

  Future<void> _onTap(TapUpDetails details) async {
    if(widget.controller.value.isInitialized) {
      showFocusCircle = true;
      x = details.localPosition.dx;
      y = details.localPosition.dy;

      double fullWidth = MediaQuery.of(context).size.width;
      double cameraHeight = fullWidth * widget.controller.value.aspectRatio;

      double xp = x / fullWidth;
      double yp = y / cameraHeight;

      Offset point = Offset(xp,yp);
      debugPrint("setting focus on: $point");

      // Manually focus
      await widget.controller.setFocusPoint(point);
      
      setState(() {
        Future.delayed(const Duration(seconds: 2)).whenComplete(() {
          setState(() {
            showFocusCircle = false;
          });
        });
      });
    }
  }
}
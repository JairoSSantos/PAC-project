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
  late Offset _center;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    _center = Offset(size.width/2, size.height/2);

    widget.controller.setFocusPoint(Offset(
      _center.dx / size.width,
      _center.dy / (size.width * widget.controller.value.aspectRatio)
    ));
    widget.controller.setFocusMode(FocusMode.locked);

    return CameraPreview(widget.controller, // Camera
      child:Stack(
        children: <Widget>[
          Positioned.fromRect(
            rect: Rect.fromCenter(
              center: _center,
              width: _imageWidth, 
              height: _imageHeight
            ), 
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.rectangle, 
                border: Border.all(color: Colors.red, width: 3)
              ),
              child: const Center(child: Icon(Icons.add, color: Colors.red)),
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
    );
  }
}
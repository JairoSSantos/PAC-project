import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:pac_app/pages/info.dart';

class CameraPage extends StatefulWidget {
  final CameraController controller;

  const CameraPage({super.key, required this.controller});

  @override
  State<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends State<CameraPage> {

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pellet Area Calculator')),
      body: Center(child: CameraPreview(widget.controller)),
      floatingActionButton: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: <Widget>[
          const Spacer(flex:3),
          FloatingActionButton(
            backgroundColor: Colors.white,
            onPressed: () {
              widget.controller.resumePreview();
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const InfoPage())
              );
            },
            heroTag: 'camera',
          ),
          const Spacer(flex:1),
          FloatingActionButton(
            backgroundColor: Colors.transparent,
            onPressed: (){},
            heroTag: 'gellery',
            child: const Icon(Icons.add_photo_alternate),
          ),
          const Spacer(flex:1)
        ]
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.miniCenterFloat,
      backgroundColor: Colors.blue,
    );
  }
}
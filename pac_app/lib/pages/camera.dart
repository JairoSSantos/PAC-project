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
  bool showFocusCircle = false;
  double x = 0;
  double y = 0;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return Scaffold(
      appBar: AppBar(title: const Text('Pellet Area Calculator')),
      body: Center(
        child: Stack(
          children: <Widget>[
            GestureDetector(
              onTapUp: (details) => _onTap(details),
              child: Stack(
                children: <Widget>[
                  Center(child: CameraPreview(widget.controller)),
                  if(showFocusCircle) Positioned(
                      top: y-20,
                      left: x-20,
                      child: Container(
                        height: 40,
                        width: 40,
                        decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white,width: 1.5)
                    ),
                  ))
                ]
              )),
            CustomPaint(painter: RectPainter(x: size.width/2, y: 250))
          ]
        )
      ),
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
      backgroundColor: Colors.blue,
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
      debugPrint("point : $point");

      // Manually focus
      await widget.controller.setFocusPoint(point);
      
      // Manually set light exposure
      //controller.setExposurePoint(point);
      
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

class RectPainter extends CustomPainter {
  final double x, y;

  const RectPainter({required this.x, required this.y});

  @override
  void paint(Canvas canvas, Size size) {
    var paint0 = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;
    //a rectangle
    canvas.drawRect(Rect.fromCenter(center: Offset(x, y), width: 256, height: 256), paint0);
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) => true;
}
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:pac_app/config.dart';
import 'package:pac_app/pages/info_page.dart';

class Cropper extends StatefulWidget {
  final XFile imageXFile;

  const Cropper({super.key, required this.imageXFile});

  @override
  State<Cropper> createState() => _CropperState();
}

class _CropperState extends State<Cropper> {

  late double _left;
  late double _top;

  @override
  Widget build(BuildContext context) {

    final screenSize = MediaQuery.of(context).size;
    final imageSize = getImageSize(widget.imageXFile.path);
    final alpha = screenSize.width/imageSize.width;
    final pelletField = Target(
      width: Default.imageWidth*alpha,
      height: Default.imageHeight*alpha
    );

    _left = (screenSize.width - pelletField.width)/2;
    _top = (screenSize.height - pelletField.height)/2;

    final imageWidget = Image.file(File(widget.imageXFile.path));

    return Scaffold(
      body: Stack(
        children: <Widget>[
          Center(child: imageWidget),
          StatefulBuilder(
            builder: (context, setNewState) => Positioned(
              left: _left,
              top: _top,
              child: GestureDetector(
                onPanUpdate: (details) => setNewState(() {
                    //debugPrint('$_left, $_top');
                    _left += details.delta.dx;
                    _top += details.delta.dy;
                }),
                child: pelletField,
              ),
            )
          ),
        ]
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final tempDir = await getTemporaryDirectory();
          final imagePath = p.join(tempDir.path, widget.imageXFile.name);
          regularizeImage(widget.imageXFile.path, 
            left: _left/alpha,
            top: (_top - (screenSize.height - screenSize.width*imageSize.height/imageSize.width)/2)/alpha,
            finalPath: imagePath
          ).then((_) {
              //Navigator.pop(context);
              Navigator.push(
              context, 
              MaterialPageRoute(
                builder: (context) => InfoPage(imagePath: imagePath)
              )
            );
          });
        }, 
        child: const Icon(Icons.crop)
      ),
    );
  }
}
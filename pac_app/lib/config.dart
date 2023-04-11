import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;

class Default{
  static const double imageHeight = 256;
  static const double imageWidth = 256;
  static const int _resolutionIndex = 2;
  static const String unit = 'mm';

  // Informações extraídas de https://pub.dev/documentation/camera_platform_interface/latest/camera_platform_interface/ResolutionPreset.html
  static final _resolutionSize = <ResolutionPreset, Size>{
    ResolutionPreset.low: Platform.isIOS ? const Size(288, 352) : const Size(240, 320),
    ResolutionPreset.medium: Platform.isIOS ? const Size(480, 640) : const Size(480, 720),
    ResolutionPreset.high: const Size(720, 1280),
    ResolutionPreset.veryHigh: const Size(1080, 1920),
    ResolutionPreset.ultraHigh: Platform.isAndroid || Platform.isIOS ? const Size(2160, 3840) : const Size(2160, 4096)
  };

  static ResolutionPreset getResolution() => ResolutionPreset.values[_resolutionIndex];

  static Size? getResolutionSize() => _resolutionSize[getResolution()];
}

Size getImageSize(String imagePath){
  final imageBytes = img.decodeImage(File(imagePath).readAsBytesSync())!;
  return Size(
    imageBytes.width.toDouble(),
    imageBytes.height.toDouble()
  );
}

class Regularizer {
  final String imagePath;
  late img.Image imageBytes;
  
  Regularizer({required this.imagePath}){
    imageBytes = img.decodeImage(File(imagePath).readAsBytesSync())!;
  }

  void crop({double? left, double? top, double? width, double? height}){
    /*
    Se [left] e [top] não forem passados, o corte será centralizado na imagem.
    Se [width] e [height] não forem passados, o tamanho do corte será o padrão.
    */
    width = width ?? Default.imageWidth;
    height = height ?? Default.imageHeight;

    imageBytes = img.copyCrop(
      imageBytes,
      x: left?.toInt() ?? (imageBytes.width - width)~/2,
      y: top?.toInt() ?? (imageBytes.height - height)~/2,
      width: width.toInt(),
      height: height.toInt(), 
    );
  }

  void resize({double? width, double? height}){
    /*
    Se [width] e [height] não forem passados, o tamanho do corte será o padrão.
    */
    imageBytes = img.copyResize(
      imageBytes,
      width: (width ?? Default.imageWidth).toInt(),
      height: (height ?? Default.imageHeight).toInt(),
    );
  }

  void save({String? savePath}) async {
    await File(savePath ?? imagePath).writeAsBytes(img.encodeJpg(imageBytes));
  }
}

// ignore: must_be_immutable
class Target extends StatefulWidget {
  final double width;
  final double height;
  var scaleFactor = 1.0;

  Target({super.key, required this.width, required this.height});

  @override
  State<Target> createState() => _TargetState();
}

class _TargetState extends State<Target> {

  late double _baseScaleFactor;
  late bool _zoomMode;

  @override
  void initState(){
    widget.scaleFactor = _baseScaleFactor = 1;
    _zoomMode = false;
    super.initState();
  }

  void initZoom(_) => setState(() {
    _baseScaleFactor = widget.scaleFactor;
  });

  void updateZoom(details) => setState(() {
    if (_zoomMode) {
      widget.scaleFactor = (_baseScaleFactor * details.scale).clamp(1, 5);
    }
  });

  void resetZoomState() => setState(() {
    _baseScaleFactor = widget.scaleFactor = 1;
  });

  void setZoomMode({bool? value}) => setState(() {
    _zoomMode = value ?? !_zoomMode;
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onScaleStart: initZoom,
      onScaleUpdate: updateZoom,
      onTap: setZoomMode,
      onDoubleTap: resetZoomState,
      onScaleEnd: (_) => setZoomMode(value: false),
      child: Center(
          child: Container(
            decoration: BoxDecoration(
              shape: BoxShape.rectangle, 
              border: Border.all(color: Colors.white, width: 1.5)
            ),
            child: Container(
              width: widget.width * widget.scaleFactor,
              height: widget.height * widget.scaleFactor,
              decoration: BoxDecoration(
                  shape: BoxShape.rectangle, 
                  border: Border.all(color: _zoomMode? Colors.blue : Colors.deepOrange, width: 3)
                ),
              child: const Center(child: Icon(Icons.add, color: Colors.deepOrange))
            )
          )
        ),
    );
  }
}
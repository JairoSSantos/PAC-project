import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;

const double _imageHeight = 256;
const double _imageWidth = 256;
const int _resolutionIndex = 2;

// Informações extraídas de https://pub.dev/documentation/camera_platform_interface/latest/camera_platform_interface/ResolutionPreset.html
final _resolutionSize = <ResolutionPreset, Size>{
  ResolutionPreset.low: Platform.isIOS ? const Size(288, 352) : const Size(240, 320),
  ResolutionPreset.medium: Platform.isIOS ? const Size(480, 640) : const Size(480, 720),
  ResolutionPreset.high: const Size(720, 1280),
  ResolutionPreset.veryHigh: const Size(1080, 1920),
  ResolutionPreset.ultraHigh: Platform.isAndroid || Platform.isIOS ? const Size(2160, 3840) : const Size(2160, 4096)
};

double getImageHeight() => _imageHeight;

double getImageWidth() => _imageWidth;

int getResolutionIndex() => _resolutionIndex;

Size? getResolutionSize() => _resolutionSize[ResolutionPreset.values[getResolutionIndex()]];

Future<void> regularizeImage(String imagePath) async {
  final resolution = getResolutionSize();

  int offsetX = (resolution?.width ?? 0)~/2 - getImageWidth()~/ 2;
  int offsetY = (resolution?.height ?? 0)~/2 - getImageHeight()~/ 2;

  final imageBytes = img.decodeImage(File(imagePath).readAsBytesSync())!;

  img.Image cropOne = img.copyCrop(
    imageBytes,
    x: offsetX,
    y: offsetY,
    width: getImageWidth().toInt(),
    height: getImageHeight().toInt(), 
  );

  File(imagePath).writeAsBytes(img.encodeJpg(cropOne));
}
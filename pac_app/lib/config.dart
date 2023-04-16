import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;

Size getImageSize(String imagePath){
  final imageBytes = img.decodeImage(File(imagePath).readAsBytesSync())!;
  return Size(
    imageBytes.width.toDouble(),
    imageBytes.height.toDouble()
  );
}

class Default{
  static const double imageHeight = 256;
  static const double imageWidth = 256;
  static const Size imageSize = Size(imageWidth, imageHeight);
  static const String unit = 'mm';
}

class PyParamConfig<T>{
  final String name;
  final T defaultValue;
  final T min;
  final T max;
  final String label;

  const PyParamConfig(this.name, this.defaultValue, this.min, this.max, this.label);
}

class PyParam<T> extends PyParamConfig<T>{
  late T value;

  PyParam(super.name, super.defaultValue, super.min, super.max, super.label){
    value = defaultValue;
  }

  static PyParam fromConfig(PyParamConfig config){
    return PyParam(config.name, config.defaultValue, config.min, config.max, config.label);
  }
} 

class PyFunction{
  final String source;
  final String name;
  late List<PyParam> params;
  final String label;

  PyFunction({required this.source, required this.name, required List<PyParamConfig<dynamic>> paramsConfig, required this.label}){
    params = paramsConfig.map((config) => PyParam.fromConfig(config)).toList();
  }

  Map asMap(){
    return {
      'source': source,
      'params': {for (final PyParam param in params) param.name: param.value}
    };
  }
}

enum Morphology {
  areaOpening('morphology', 'area_opening', 'Remover excessos', [PyParamConfig<int>('area_threshold', 64, 0, 1000, 'Tamanho')]),
  areaClosing('morphology', 'area_closing', 'Remover buracos', [PyParamConfig<int>('area_threshold', 64, 0, 1000, 'Tamanho')]);

  const Morphology(this.source, this.name, this.label, this.paramsConfig);
  final String source;
  final String name;
  final String label;
  final List<PyParamConfig> paramsConfig;

  PyFunction pyFunc() => PyFunction(
    source: source, 
    name: name, 
    paramsConfig: paramsConfig,
    label: label
  );
}
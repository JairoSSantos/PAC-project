import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:shared_preferences/shared_preferences.dart';

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
  static String unit = 'mm';
  static int precision = 3;
  static String sampleName = 'Unnamed';

  static dynamic getParamByName(String name) => {
    'unit': unit,
    'precision': precision,
  }[name];

  static Map<String, String> get paramLabels => {
    'unit': 'unidade',
    'precision': 'precisão'
  };

  static dynamic getParamLabel(String name) => paramLabels[name];

  static setParamByName(String name, dynamic value) {
    if (name == 'unit'){
      unit = value;
    } else if (name == 'precision') {
      precision = int.parse(value);
    }
  }

  static Future<String> get ipAddress async {
    return (await SharedPreferences.getInstance()).getString('ipAdress') ?? '127.0.0.1';
  }

  static Future<String> get port async {
    return (await SharedPreferences.getInstance()).getString('port') ?? '5000';
  }

  static set ipAddress(newIp) {
    SharedPreferences.getInstance().then((pref) => pref.setString('ipAdress', newIp));
  }

  static set port(newPort) {
    SharedPreferences.getInstance().then((pref) => pref.setString('port', newPort));
  }
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
  areaOpening('morphology', 'area_opening', 'Remover excessos', [PyParamConfig<int>('area_threshold', 64, 0, 2000, 'Tamanho')]),
  areaClosing('morphology', 'area_closing', 'Remover buracos', [PyParamConfig<int>('area_threshold', 64, 0, 2000, 'Tamanho')]),
  binaryOpening('ndimage', 'binary_opening', 'Aparar bordas', [PyParamConfig<int>('iterations', 1, 1, 20, 'Iterações')]);

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
import 'package:flutter/material.dart';
import 'package:pac_app/pages/camera.dart';

void main() => runApp(const PacApp());

class PacApp extends StatelessWidget {
  const PacApp({super.key});

  @override
  Widget build(BuildContext context){
    return const MaterialApp(
      title: 'Pellet Area Calculator',
      home: CameraPage()
    );
  }
}
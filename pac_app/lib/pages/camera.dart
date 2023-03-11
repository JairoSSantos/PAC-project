import 'package:flutter/material.dart';
import 'package:pac_app/pages/info.dart';

class CameraPage extends StatefulWidget {
  const CameraPage({super.key});

  @override
  State<CameraPage> createState() => _CameraPageState();
}

class _CameraPageState extends State<CameraPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pellet Area Calculator')),
      body: const Placeholder(),
      floatingActionButton: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: <Widget>[
          const Spacer(flex:3),
          FloatingActionButton(
            onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const InfoPage())
            )
          ),
          const Spacer(flex:1),
          FloatingActionButton(
            backgroundColor: Colors.transparent,
            onPressed: (){},
            child: const Icon(Icons.image_search)
          ),
          const Spacer(flex:1)
        ]
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
}
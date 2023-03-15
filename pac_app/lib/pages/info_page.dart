import 'package:flutter/material.dart';
import 'package:pac_app/config.dart';
import 'package:flutter_speed_dial/flutter_speed_dial.dart';
import 'dart:io';

// ignore: must_be_immutable
class InfoPage extends StatefulWidget {
  late String imagePath;

  InfoPage({super.key, required this.imagePath});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  final _infoMessages = [
    'Área: 0.00',
    'Escala: 0.00',
    'Erro estimado: 0.00'
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Resultado')),
      body: Column(
        children: <Widget>[
          Image.file(File(widget.imagePath), 
            /*fit: BoxFit.contain, 
            width: getImageWidth(), 
            height: getImageHeight()*/
          ),
          SizedBox(
            height: 350,
            child: ListView.builder(
                itemBuilder: (context, index) => Card(child: ListTile(title: Text(_infoMessages[index]))), 
                itemCount: _infoMessages.length
            )
          )
        ]
      ),
      floatingActionButton: SpeedDial(
        icon: Icons.save,
        children: <SpeedDialChild>[
          SpeedDialChild(
            label: 'Salvar imagem',
            child: const Icon(Icons.add_photo_alternate_outlined)
          ),
          SpeedDialChild(
            label: 'Salvar resultado como imagem',
            child: const Icon(Icons.photo_library_outlined)
          ),
          SpeedDialChild(
            label: 'Salvar resultado como pdf',
            child: const Icon(Icons.picture_as_pdf_outlined)
          )
        ]
      ),
    );
  }
}
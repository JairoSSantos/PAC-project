import 'package:flutter/material.dart';

class InfoPage extends StatefulWidget {
  const InfoPage({super.key});

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
    final size = MediaQuery.of(context).size;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Resultado'),
        actions: <Widget>[
          PopupMenuButton(
            itemBuilder: (context) => [
              const PopupMenuItem(child: Text('Salvar imagem')),
              const PopupMenuItem(child: Text('Salvar resultado como imagem')),
              const PopupMenuItem(child: Text('Salvar resultado como PDF'))
            ]
          )
        ]
      ),
      body: Column(
        children: <Widget>[
          const Placeholder(),
          Container(
            height: 300,
            child: ListView.builder(
                itemBuilder: (context, index) => Card(child: ListTile(title: Text(_infoMessages[index]))), 
                itemCount: _infoMessages.length
            )
          )
        ]
      )
    );
  }
}
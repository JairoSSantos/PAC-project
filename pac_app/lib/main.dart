import 'package:flutter/material.dart';

void main() => runApp(const PacApp());

class PacApp extends StatelessWidget {
  const PacApp({super.key});

  @override
  Widget build(BuildContext context){
    return MaterialApp(
      title: 'Pellet Area Calculator',
      theme: ThemeData(primarySwatch: Colors.orange),
      home: const CameraPage()
    );
  }
}

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
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const InfoPage()),
          );
        },
        backgroundColor: Colors.blue
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat
    );
  }
}

class InfoPage extends StatefulWidget {
  const InfoPage({super.key});

  @override
  State<InfoPage> createState() => _InfoPageState();
}

class _InfoPageState extends State<InfoPage> {

  final _info = [
    'Área: 0.00',
    'Escala: 0.00',
    'Erro estimado: 0.00'
  ];

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: <Widget>[
        SliverAppBar(
          floating: false,
          pinned: true,
          snap: false,
          expandedHeight: MediaQuery.of(context).size.width,
          flexibleSpace: const Flexible(
            child: Placeholder()
          ),
        ),
        SliverList(
          delegate: SliverChildBuilderDelegate(
            (context, index) => Container(
                color: Colors.white,
                child: Text(
                  _info[index], 
                  textAlign: TextAlign.left, 
                  style: const TextStyle(color: Colors.blue, fontSize: 28)
                ),
              ),
            childCount: _info.length
          )
        )
      ],
    );
  }
}
from mininet.topo import Topo

class VM1_topo( Topo ):
    "Simple topology example."

    def build( self ):
        "Create custom topo."

        # Add hosts and switches
        h1 = self.addHost( 'h1' )
        h2 = self.addHost( 'h2' )
        h3 = self.addHost( 'h3' )
        h4 = self.addHost( 'h4' )
        s1 = self.addSwitch( 's1' )

        # Add links
        self.addLink( s1, h1 )
        self.addLink( s1, h2 )
        self.addLink( s1, h3 )
        self.addLink( s1, h4 )

class VM2_topo( Topo ):
    "Simple topology example."

    def build( self ):
        "Create custom topo."

        # Add hosts and switches
        h5 = self.addHost( 'h5', ip='10.0.2.5' )
        h6 = self.addHost( 'h6', ip='10.0.2.6' )
        h7 = self.addHost( 'h7', ip='10.0.2.7' )
        h8 = self.addHost( 'h8', ip='10.0.2.8' )
        s2 = self.addSwitch( 's2' )

        # Add links
        self.addLink( s2, h5 )
        self.addLink( s2, h6 )
        self.addLink( s2, h7 )
        self.addLink( s2, h8 )


topos = { 'vm1': ( lambda: VM1_topo()), 'vm2': (lambda:VM2_topo()) }
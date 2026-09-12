"""Build the PDF, readable source and PGN. Run with Python 3.11+.

Dependencies: reportlab, chess, svglib, pypdf.
CHESS_COURSE_PACKAGES can point to a task-local dependency directory.
"""
from pathlib import Path
import os, sys, io, json, re
if os.environ.get('CHESS_COURSE_PACKAGES'):
    sys.path.insert(0, os.environ['CHESS_COURSE_PACKAGES'])
import chess, chess.svg, chess.pgn
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from pypdf import PdfReader
import reportlab

OUT = Path(__file__).resolve().parent
PDF = OUT / 'when-to-trade-and-take.pdf'
W, H = 612, 792
INK = '#172F36'
TEAL = '#176F69'
MUTED = '#52646A'
LIGHT = '#EAF2EF'
GOLD = '#BC773D'
PAPER = '#FAF9F5'
FONTDIR = Path(reportlab.__file__).parent / 'fonts'
for name, filename in [('Body','Vera.ttf'),('Bold','VeraBd.ttf'),('Italic','VeraIt.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONTDIR / filename)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')
styles = {
    'body': ParagraphStyle('body',fontName='Body',fontSize=10.1,leading=15.1,textColor=colors.HexColor(INK),spaceAfter=0),
    'small': ParagraphStyle('small',fontName='Body',fontSize=8.6,leading=12.5,textColor=colors.HexColor(MUTED)),
    'large': ParagraphStyle('large',fontName='Body',fontSize=12,leading=18,textColor=colors.HexColor(INK)),
    'white': ParagraphStyle('white',fontName='Body',fontSize=11.5,leading=18,textColor=colors.white),
}
c = canvas.Canvas(str(PDF),pagesize=(W,H),pageCompression=1)
c.setTitle('When to Trade & When to Take | A Practical Chess Course')
c.setAuthor('Chess study course')
c.setSubject('Captures, exchanges, pawn tension, recaptures and endgames; beginner to intermediate')
page = 0
markdown = []
checks = []
pgn_games = []

def txt(s,x,y,size=10,font='Body',color=INK):
    c.setFillColor(colors.HexColor(color)); c.setFont(font,size)
    c.drawString(x,H-y-size*.82,s)

def para(s,x=48,y=135,w=516,style='body',record=True):
    p=Paragraph(s,styles[style]); _,h=p.wrap(w,700)
    assert y+h <= 729, ('Text exceeds body',page,y,h,s[:100])
    p.drawOn(c,x,H-y-h)
    if record: markdown.append(re.sub('<[^>]*>','',s))
    return y+h

def rule(y=736):
    c.setStrokeColor(colors.HexColor('#CFDAD7')); c.setLineWidth(.6)
    c.line(48,H-y,564,H-y)

def begin(kicker,title,sub=''):
    global page
    if page: c.showPage()
    page+=1
    c.setFillColor(colors.HexColor(PAPER)); c.rect(0,0,W,H,fill=1,stroke=0)
    txt('TRADE / TAKE',48,30,8,'Bold',TEAL)
    txt(kicker.upper(),365,30,8,'Bold',MUTED)
    txt(title,48,64,25,'Bold')
    if sub: para(sub,48,101,516,'small',False)
    rule()
    txt('WHEN TO TRADE & WHEN TO TAKE',48,752,7,'Bold',MUTED)
    txt(f'{page:02d}',544,749,11,'Bold',TEAL)
    c.bookmarkPage(f'p{page}')
    c.addOutlineEntry(title,f'p{page}',0,False)
    markdown.extend(['',f'# {page}. {title}',sub,''])

def section(title,body,y,x=48,w=516):
    txt(title,x,y,13,'Bold',TEAL)
    markdown.append('## '+title)
    return para(body,x,y+23,w)+19

def callout(label,body,y=649,h=69):
    c.setFillColor(colors.HexColor(LIGHT)); c.roundRect(48,H-y-h,516,h,8,fill=1,stroke=0)
    txt(label.upper(),62,y+11,8,'Bold',TEAL)
    para(body,62,y+29,488,'body')

def position(fen=None,moves=None):
    b=chess.Board(fen) if fen else chess.Board()
    for move in (moves or '').split(): b.push_san(move)
    assert b.is_valid(), ('Invalid position',b.fen(),b.status())
    return b

def line(b,san,tag,result=None):
    p=b.copy(); start=p.fen(); tokens=san.split()
    g=chess.pgn.Game(); g.setup(p)
    g.headers['Event']=tag; g.headers['Site']='Teaching position'
    g.headers['Date']='2026.09.12'; g.headers['White']='White'; g.headers['Black']='Black'
    node=g
    for token in tokens:
        move=p.parse_san(token)
        assert move in p.legal_moves,(tag,token,p.fen())
        assert p.san(move)==token,(tag,token,p.san(move))
        node=node.add_variation(move); p.push(move)
    if result=='stalemate': assert p.is_stalemate(),tag
    if result=='dead': assert p.is_insufficient_material(),tag
    if result=='mate': assert p.is_checkmate(),tag
    g.headers['Result']=p.result() if p.is_game_over() else '*'
    g.comment='Illustrative line. See the PDF for the question, alternatives and limits of the claim.'
    pgn_games.append(g)
    checks.append({'label':tag,'start_fen':start,'san':san,'end_fen':p.fen(),'assertion':result or 'legal line'})
    return p

def board(b,x,y,size=224,marks=()):
    fill={chess.parse_square(s):'#e5bd75aa' for s in marks}
    svg=chess.svg.board(b,size=size,coordinates=True,fill=fill,colors={
        'square light':'#F0EEE5','square dark':'#83A49A',
        'margin':'#FAF9F5','coord':'#52646A'})
    drawing=svg2rlg(io.StringIO(svg))
    factor=size/drawing.width
    drawing.scale(factor,factor)
    drawing.width=size; drawing.height=size
    renderPDF.draw(drawing,c,x,H-y-size)
    markdown.append('Position (White at bottom): `'+b.fen()+'`')

def case(label,b,body,y,marks=()):
    txt(label,48,y,12,'Bold',TEAL); markdown.append('## '+label)
    board(b,48,y+25,224,marks)
    para(body,292,y+29,272)

def note_lines(y=666,n=2,x=292,w=272):
    c.setStrokeColor(colors.HexColor('#CFDAD7')); c.setLineWidth(.5)
    for i in range(n): c.line(x,H-y-i*22,x+w,H-y-i*22)

# Reusable teaching positions. Opening positions are generated from legal moves.
free=position('6k1/5ppp/8/4n3/8/5N2/5PPP/6K1 w - - 0 1')
ledger=position('6k1/5ppp/3p4/4p3/8/2B2N2/5PPP/6K1 w - - 0 1')
pin=position('4k3/4n3/8/3p4/5N2/8/5PPP/4R1K1 w - - 0 1')
between=position('3qr1k1/5p1p/8/8/3n4/7P/5PP1/3QR1K1 w - - 0 1')
tension=position(moves='d4 d5 c4 e6 Nc3 Nf6 Nf3')
ruy=position(moves='e4 e5 Nf3 Nc6 Bb5 a6 Bxc6')
after_ruy=position(moves='e4 e5 Nf3 Nc6 Bb5 a6 Bxc6 dxc6')
qend=position('2kq4/8/3QK3/4P3/8/8/8/8 w - - 0 1')
qdraw=position('kq6/8/PK1Q4/8/8/8/8/8 w - - 0 1')
dead=position('4rk2/8/8/8/2B5/8/8/4R1K1 w - - 0 1')
stale=position('7k/8/5Kp1/6Q1/8/8/8/8 w - - 0 1')
mate=position('6k1/5ppp/8/8/8/8/5PPP/3bR1K1 w - - 0 1')
line(free,'Nxe5','Lesson 1 - free knight')
line(ledger,'Nxe5 dxe5 Bxe5','Lesson 1 - count the full exchange')
line(pin,'Nxd5','Lesson 2 - pinned defender')
bp=pin.copy(); bp.push_san('Nxd5')
assert chess.Move.from_uci('e7d5') not in bp.legal_moves
line(between,'Rxe8+ Qxe8 Qxd4 Qe1+ Kh2','Lesson 2 - capture with check first')
line(between,'Qxd4 Qxd4 Rxe8+ Kg7','Lesson 2 - wrong move order')
line(tension,'Be7 cxd5 exd5','Lesson 4 - release the tension')
line(tension,'Be7 Bg5','Lesson 4 - maintain the tension')
line(ruy,'dxc6','Lesson 5 - d-pawn recapture')
line(ruy,'bxc6','Lesson 5 - b-pawn recapture')
line(after_ruy,'Nxe5 Qd4 Nf3 Qxe4+','Lesson 5 - the e5 pawn is not free')
line(qend,'Qxd8+ Kxd8 Kf7 Kd7 e6+ Kd6 e7 Kd7 e8=Q+','Lesson 6 - playable winning pawn ending')
line(qdraw,'Qxb8+ Kxb8 a7+ Ka8 Ka6','Lesson 6 - rook-pawn drawing trap','stalemate')
line(dead,'Rxe8+ Kxe8','Lesson 7 - last rook traded','dead')
line(stale,'Qxg6','Lesson 8 - capture causes stalemate','stalemate')
line(stale,'Kxg6 Kg8','Lesson 8 - capture preserves legal reply')
line(mate,'Re8#','Lesson 8 - checkmate before material','mate')
line(mate,'Rxd1','Lesson 8 - ordinary capture')

# 1 / cover
begin('A practical chess course','When to trade', '')
txt('& when to take',48,101,31,'Bold')
para('Make captures with a reason.<br/>Choose exchanges for the position they create.',48,158,485,'large')
board(after_ruy,48,242,320,('c6','e5'))
c.setFillColor(colors.HexColor(INK)); c.roundRect(388,H-265-266,176,266,10,fill=1,stroke=0)
txt('THE CORE HABIT',403,283,9,'Bold','#B7D6CB')
para('Before you take,<br/>see the reply.<br/><br/>Before you trade,<br/>see what remains.',403,319,146,'white')
para('BEGINNER TO INTERMEDIATE',48,605,516,'small')
para('8 lessons  /  10 exercises  /  explained answers<br/>A decision sheet and a seven-day practice plan',48,631,516,'large')
para('Designed for players who know how the pieces move. Study with a board and write down your reasoning.',48,699,516,'small')

# 2 / route
begin('Start here','Your route through the course','A capture removes an enemy unit. An exchange is a sequence in which both sides give up material.')
y=135
y=section('What you will learn','Decide whether a capture is safe; calculate a complete exchange; compare piece activity and pawn structure; choose a recapture; and inspect the endgame before simplifying.',y)
y=section('Study in three passes','<b>First:</b> read the method and lessons on pages 3-11 with a board.<br/><b>Second:</b> solve pages 12-16 without the answers. Allow 2-4 minutes per position.<br/><b>Third:</b> check pages 17-19, then apply the review routine on page 20.',y)
y=section('Read the moves','<b>K</b> = king, <b>Q</b> = queen, <b>R</b> = rook, <b>B</b> = bishop, <b>N</b> = knight. Pawns have no letter. <b>Nxe5</b> means a knight captures on e5. <b>dxc6</b> means the d-pawn captures on c6. <b>+</b> = check; <b>#</b> = checkmate; <b>O-O</b> = kingside castling; <b>e8=Q</b> = promotion to a queen. <b>1...</b> starts with Black\'s move. [1]',y)
y=section('Board and exercise conventions','White is at the bottom in every diagram; a1 is at the lower left. The side to move is stated in each example. Highlighted squares identify a lesson\'s focus. The sparse positions isolate one idea. Strategic questions can have more than one reasonable move.',y)
callout('Working rule','State a move, the opponent\'s best reply, and one consequence for the resulting position.',650)

# 3 / method
begin('Decision method','The five-question check','Use this before committing to a capture, accepting a trade or automatically recapturing.')
y=136
for title,body in [
('01  Is my king safe?','If you are in check, your move must answer it. After any candidate move, check whether moving that piece opens a line to your own king.'),
('02  What is the strongest reply?','Look for the opponent\'s checks, captures and immediate threats. Do not assume a recapture. Identify pins, overloaded defenders and newly opened lines.'),
('03  What is the final material balance?','Follow the sequence until the immediate tactics settle. Total everything won and lost. Count units only after checking which defenders can legally act.'),
('04  Who likes the remaining position?','Compare king safety, piece activity, pawn structure and the endgame. Include the piece that recaptures: it may become the best piece on the board.'),
('05  Is there a better alternative?','Compare taking now, maintaining the tension and improving a piece. Choose the move with the strongest concrete justification.')]:
    y=section(title,body,y)
callout('Your decision sentence','"I will play ___ because after ___, the resulting position gives me ___."',650)

# 4 / counting
begin('Lesson 1 / material','Count the whole transaction','Starting estimates: pawn 1, knight 3, bishop 3, rook 5, queen 9. The king has no trade value. [2]')
case('A. A genuinely available piece | White to move',free,'<b>1.Nxe5</b> takes an undefended knight. Black has no immediate recapture on e5.<br/><br/>White gains a knight, about 3 points. Still scan the whole board: an undefended target is a candidate, not proof that a capture is best.<br/><br/><b>Habit:</b> after visualizing the move, check the opponent\'s forcing replies.',136,('e5',))
case('B. A long sequence can lose material | White to move',ledger,'Consider <b>1.Nxe5 dxe5 2.Bxe5</b>.<br/><br/>White wins two pawns (2) and loses a knight (3). The net change is <b>2 - 3 = -1</b>.<br/><br/>Do not call this an equal trade because White makes the final capture. This line needs separate compensation to justify it; the pawn count alone does not.',407,('d6','e5'))
para('Piece values are estimates, not rules that override checkmate, tactical consequences or a forced draw.',48,698,516,'small')

# 5 / tactical replies
begin('Lesson 2 / calculation','Defenders and move order','Counting attackers is a starting point. Legal moves and forcing replies decide the result.')
case('A. The apparent defender is pinned | White to move',pin,'<b>1.Nxd5</b> wins the pawn. The e7-knight appears to defend d5, but <b>...Nxd5 is illegal</b>: it would expose Black\'s king to the e1-rook.<br/><br/>This is an absolute pin. A piece pinned to a queen can still move legally; calculate what that move threatens.<br/><br/>Recheck pins after each capture. They can disappear.',136,('e7','d5'))
case('B. Insert the forcing capture | White to move',between,'Start with <b>1.Rxe8+!</b> After <b>1...Qxe8 2.Qxd4</b>, White has traded rooks and won the knight. A king move instead leaves the queen on d8 to the rook.<br/><br/>By contrast, <b>1.Qxd4? Qxd4 2.Rxe8+ Kg7</b> gives a queen (9) for a knight and rook (8).<br/><br/>Check the return check too: <b>2...Qe1+ 3.Kh2</b> is safe. The h3-pawn gives the king an escape. [3]',407,('e8','d4'))

# 6 / quality
begin('Lesson 3 / strategy','Equal value, unequal usefulness','A three-point piece may do much more work than another three-point piece.')
y=138
y=section('Trade your least useful piece for their strongest','A passive bishop for an entrenched knight can be attractive. Compare its square, targets and mobility. Then inspect the recapture. It might create a passed pawn: a pawn with no enemy pawn ahead on its file or either neighboring file.',y)
y=section('Remove a defender when the follow-up works','A trade can expose a king or make a target fall. Calculate the follow-up before exchanging. If another unit can replace the defender, the trade may achieve little.',y)
y=section('Keep the pieces that make your plan work','An attacking bishop, an active rook or a knight on an outpost can outperform its nominal value. An outpost is a useful square that enemy pawns cannot easily challenge. Keep the piece if its role matters more than the offered exchange.',y)
y=section('Measure the cost of the recapture','A trade can double enemy pawns but open a useful file, develop a bishop or bring a king toward the center. Compare all of those changes. A visible pawn weakness is only valuable if you can exploit it.',y)
y=section('Use space as a clue','With less room, exchanges can ease congestion. With more room, keeping pieces can maintain the squeeze. These are tendencies; a concrete tactical gain or a favorable endgame can outweigh them.',y)
callout('Mini exercise','Name your best piece and your opponent\'s best piece in a recent game. Which proposed exchange would change that comparison?',651)

# 7 / tension
begin('Lesson 4 / pawn tension','You do not have to take yet','Tension means opposing units can capture each other. Keeping it preserves choices.')
board(tension,48,144,251,('c4','d5'))
para('<b>Black to move.</b> After<br/>1.d4 d5 2.c4 e6 3.Nc3 Nf6 4.Nf3<br/><br/>Use <b>4...Be7</b> as a normal developing move. White can then compare <b>5.cxd5</b> with <b>5.Bg5</b>.<br/><br/>This is a choice of plans. Neither a capture nor a quiet move is automatically correct.',322,150,242)
y=426
y=section('Taking now: 5.cxd5 exd5','A half-open file has no friendly pawns and at least one enemy pawn. After the exchange, the c-file is half-open for White and the e-file for Black. Black\'s c8-bishop gains a cleared diagonal through d7 and e6. White should have a plan for the new structure.',y)
y=section('Keeping the tension: 5.Bg5','White develops a piece and retains the c4-pawn\'s pressure on d5. The decision to exchange can come later. Continue checking whether Black can capture, advance or use a tactic against the center.',y)
callout('When to release it','Take when you win something concrete, improve the resulting structure, prevent a favorable enemy break or reach an ending you want.',650)

# 8 / recapture
begin('Lesson 5 / recapturing','Choose the unit that retakes','"Capture toward the center" is a useful starting idea, never a substitute for comparing the board.')
board(ruy,48,140,244,('b7','d7','c6'))
para('<b>Black to move.</b> Ruy Lopez Exchange Variation:<br/>1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Bxc6<br/><br/><b>4...dxc6:</b> opens the d-file and the c8-bishop\'s diagonal.<br/><br/><b>4...bxc6:</b> opens the b-file and retains the d-pawn, which can influence the center.<br/><br/>Both recaptures leave doubled c-pawns. Their other effects differ.',313,145,251)
y=414
y=section('Compare four consequences','<b>King:</b> do I open my own shelter?<br/><b>Activity:</b> which piece or file becomes available?<br/><b>Structure:</b> do I create isolated, doubled or passed pawns?<br/><b>Tactics:</b> is an intermediate move stronger than either recapture?',y)
y=section('A tempting follow-up is not a free pawn','After <b>4...dxc6</b>, try <b>5.Nxe5? Qd4</b>. Black attacks the knight and the e4-pawn. In <b>6.Nf3 Qxe4+</b>, Black recovers the pawn with check. This illustrates why removing a defender does not finish the calculation.',y)
callout('Before recapturing','Compare every legal recapture. Include a check, threat or counter-capture if it changes the result.',650)

# 9 / endgame preview
begin('Lesson 6 / queen trades','Preview the endgame first','Remove the queens in your mind, place the recapturing piece correctly, and evaluate that exact position.')
case('A. A clear plan after the queens go | White to move',qend,'<b>1.Qxd8+ Kxd8 2.Kf7</b> reaches a winning king-and-pawn ending. White\'s king controls the route ahead of the pawn.<br/><br/>One illustrative continuation is <b>2...Kd7 3.e6+ Kd6 4.e7 Kd7 5.e8=Q+</b>.<br/><br/>Black has other king moves; the principle is to keep the king supporting the pawn\'s advance.',136,('d8','e5'))
case('B. An extra rook-pawn may be insufficient | White to move',qdraw,'White is in check. <b>1.Qxb8+ Kxb8</b> reaches a drawn rook-pawn ending: Black can occupy a8.<br/><br/>For example, <b>2.a7+ Ka8 3.Ka6</b> is stalemate. White cannot force the king out of the corner with only this pawn and king.<br/><br/>This evaluates the resulting ending; it does not claim a forced win exists before the trade.',407,('a6','a8'))

# 10 / score of position
begin('Lesson 7 / simplifying','When ahead, when behind','Material advantage changes your priorities. It does not make every exchange helpful.')
y=137
y=section('When ahead: reduce useful enemy resources','Look for safe trades that reduce counterplay and preserve a winning plan. Keep enough material to checkmate or create a passed pawn. Trading pawns can remove your route to victory; trading an active piece can also give away control.',y)
y=section('When behind: look for specific drawing routes','Keeping active pieces often preserves threats and practical chances. But exchanges can be excellent if they remove all the opponent\'s winning material, reach a known drawn ending or eliminate a dangerous attack. "Never trade when behind" is too crude.',y)
board(dead,48,376,230,('e8','c4'))
para('<b>White to move: an extra bishop.</b><br/><br/>After <b>1.Rxe8+ Kxe8</b>, only king and bishop versus king remain. Neither side can checkmate by any legal sequence, so the game is drawn. [1]<br/><br/>The initial extra bishop does not itself prove a win. The example shows why reducing the piece count is not the same as converting an advantage.',302,385,262)
callout('Conversion question','After this exchange, what is my actual winning method? If you cannot name one, inspect the ending before trading.',650)

# 11 / final tactical safeguards
begin('Lesson 8 / exceptions','The result outranks the count','Two final checks: can I finish the game, and does this capture accidentally end it in a draw?')
case('A. A free pawn can be the wrong capture | White to move',stale,'<b>1.Qxg6?</b> is stalemate. The black king is not in check and has no legal move.<br/><br/><b>1.Kxg6</b> preserves the win. The white king now blocks the queen\'s g-file, so Black can play <b>...Kg8</b>. White retains queen and king against a bare king.<br/><br/>After a final capture, check the opponent\'s legal moves. [1]',136,('g6','h8'))
case('B. Checkmate before recapturing | White to move',mate,'White can capture the bishop with <b>1.Rxd1</b>, but <b>1.Re8#</b> ends the game at once.<br/><br/>A material loss does not oblige you to recapture on the next move. Look for checks and threats before choosing the natural capture.<br/><br/>"Checks first" is a search habit, not an instruction to play a bad check.',407,('d1','e8'))

# 12-16 / exercise positions
p1=position('6k1/5ppp/8/4b3/8/5N2/5PPP/6K1 w - - 0 1')
p2=position('6k1/5ppp/2p5/3p4/8/3R4/5PPP/3Q2K1 w - - 0 1')
p3=position('2k5/2n5/4p3/8/3N4/8/5PPP/2R3K1 w - - 0 1')
p4=position('3qr1k1/5p1p/8/3n4/8/7P/3Q1PP1/4R1K1 w - - 0 1')
p5=position(moves='e4 e5 Nf3 Nc6 Bb5 a6')
p6=position(moves='d4 d5 c4 e6 Nc3 Nf6 Nf3 Be7')
p7=position('3q2k1/5ppp/8/8/8/5b2/5PPP/3Q2K1 w - - 0 1')
p8=position('2kr4/8/8/8/8/1B6/8/3R3K w - - 0 1')
p9=position('k7/8/1pK5/1Q6/8/8/8/8 w - - 0 1')
p10=position('6k1/5ppp/8/8/8/8/5PPP/2bR2K1 w - - 0 1')
puzzles=[
('01 / Is the bishop available?',p1,'<b>White to move.</b> Assess Nxe5. Is there an immediate recapture? What material change does the move produce?<br/><br/>Write the move and one safety check.','Tactical scan'),
('02 / Who pays more?',p2,'<b>White to move.</b> Evaluate this proposed sequence:<br/><b>1.Rxd5 cxd5 2.Qxd5</b><br/><br/>List White\'s gains and losses. Does the final capture make the exchange profitable on material alone?','Material ledger'),
('03 / Can the defender actually move?',p3,'<b>White to move.</b> Is Nxe6 legal? Can Black answer ...Nxe6?<br/><br/>Name the line that changes if Black\'s knight moves.','Pins'),
('04 / Find the right order',p4,'<b>White to move.</b> Compare Qxd5 with Rxe8+.<br/><br/>Find a forcing sequence that wins the knight without losing the queen. Explain the role of the check.','Intermediate capture'),
('05 / What are you exchanging?',p5,'<b>White to move.</b> Compare 4.Bxc6 with 4.Ba4.<br/><br/>Give one benefit and one cost of Bxc6, assuming ...dxc6. Is the e5-pawn then simply free?','Strategic judgment'),
('06 / Take or develop?',p6,'<b>White to move.</b> Compare 5.cxd5 exd5 with 5.Bg5.<br/><br/>Which files become half-open after the exchange? Which option keeps the central tension?','Pawn tension'),
('07 / Choose your recapture',p7,'<b>White to move.</b> Compare Qxf3 and gxf3.<br/><br/>If neither move loses to an immediate tactic, which better preserves the king\'s pawn shelter? Describe the other recapture\'s structural cost.','Recapturing'),
('08 / An extra piece is not enough',p8,'<b>White to move.</b> What follows 1.Rxd8+ Kxd8?<br/><br/>Name the remaining material and the game result. What does this teach about exchanging while ahead?','Endgame preview'),
('09 / Take the last pawn?',p9,'<b>White to move.</b> Compare Qxb6 and Kxb6.<br/><br/>After each capture, check whether Black is in check and list any legal move.','Stalemate check'),
('10 / More urgent than taking',p10,'<b>White to move.</b> White can capture the bishop on c1.<br/><br/>Find a better move and prove the game is over.','Checks before captures'),
]
for i in range(0,10,2):
    begin(f'Practice / {i+1:02d}-{i+2:02d}','Decide, calculate, explain','Allow 2-4 minutes per diagram. Answer key: pages 17-19. White is at the bottom.')
    for j,top in [(i,137),(i+1,418)]:
        label,b,body,topic=puzzles[j]
        case(label,b,body,top)
        note_lines(top+223,2)

# Exercise solutions also become playable PGN entries.
line(p1,'Nxe5','Exercise 01 - free bishop')
line(p2,'Rxd5 cxd5 Qxd5','Exercise 02 - material ledger')
line(p3,'Nxe6','Exercise 03 - pinned knight')
bp=p3.copy();bp.push_san('Nxe6');assert chess.Move.from_uci('c7e6') not in bp.legal_moves
line(p4,'Rxe8+ Qxe8 Qxd5 Qe1+ Kh2','Exercise 04 - right move order')
line(p4,'Qxd5 Qxd5 Rxe8+ Kg7','Exercise 04 - wrong move order')
line(p5,'Bxc6 dxc6 Nxe5 Qd4 Nf3 Qxe4+','Exercise 05 - trade and follow-up')
line(p5,'Ba4','Exercise 05 - retain the bishop')
line(p6,'cxd5 exd5','Exercise 06 - release tension')
line(p6,'Bg5','Exercise 06 - develop')
line(p7,'Qxf3','Exercise 07 - queen recapture')
line(p7,'gxf3','Exercise 07 - pawn recapture')
line(p8,'Rxd8+ Kxd8','Exercise 08 - dead position','dead')
line(p9,'Qxb6','Exercise 09 - stalemate','stalemate')
line(p9,'Kxb6 Kb8','Exercise 09 - preserve the win')
line(p10,'Rd8#','Exercise 10 - mate','mate')
line(p10,'Rxc1','Exercise 10 - ordinary capture')

# 17-19 / answer key
begin('Answers / 01-04','Calculate before you judge','Award one point for the move or judgment and one for the explanation. Maximum: 20 points.')
y=137
y=section('01 / Take the bishop','<b>1.Nxe5.</b> Black has no immediate recapture on e5; White gains a bishop, about 3 points. The white king is safe. A later pawn move such as ...f6 is not a recapture: White gets another turn to move the knight.',y)
y=section('02 / The sequence loses three points','After <b>1.Rxd5 cxd5 2.Qxd5</b>, White has won two pawns (2) and lost a rook (5): <b>2 - 5 = -3</b>. No material profit exists in the stated line. White would need concrete compensation to justify starting it.',y)
y=section('03 / The defender is absolutely pinned','<b>1.Nxe6</b> is legal. Black\'s <b>...Nxe6</b> would expose the c8-king to the c1-rook along the c-file, so that reply is illegal. Do not count the c7-knight as an available recapturing defender in this position.',y)
y=section('04 / Trade rooks with check first','<b>1.Rxe8+ Qxe8 2.Qxd5</b> wins the knight. A king move instead leaves the queen on d8 to the rook. The return check <b>2...Qe1+ 3.Kh2</b> is safe: the h3-pawn gives White an escape square.<br/><br/>The tempting <b>1.Qxd5? Qxd5 2.Rxe8+ Kg7</b> costs a queen (9) for a knight and rook (8), a net loss of 1. The order matters.',y)
callout('If you missed 01-04','Return to pages 4-5. Put each captured piece beside the board and total both piles before evaluating the position.',650)

begin('Answers / 05-07','Explain the position left behind','Strategic answers are graded for sound consequences, not for guessing an engine\'s first choice.')
y=137
y=section('05 / A trade of different advantages','After <b>4.Bxc6 dxc6</b>, White has exchanged a bishop for a knight and doubled Black\'s c-pawns. Black keeps both bishops and opens lines for development. <b>4.Ba4</b> retains White\'s light-squared bishop and preserves a different structure.<br/><br/>A complete answer names both a benefit and a cost. The e5-pawn is not simply free: <b>5.Nxe5? Qd4 6.Nf3 Qxe4+</b> recovers a pawn with check.',y)
y=section('06 / Fix the structure or keep the option','<b>5.cxd5 exd5</b> leaves the c-file half-open for White and the e-file half-open for Black. It also clears the c8-bishop\'s diagonal. <b>5.Bg5</b> develops the bishop and keeps the central pawn tension.<br/><br/>Neither answer is justified by "I always take" or "I never take." Identify which resulting structure fits your plan.',y)
y=section('07 / Preserve the pawn shelter','<b>1.Qxf3</b> captures with the queen and keeps f2, g2 and h2 intact. <b>1.gxf3</b> leaves doubled f-pawns on f2 and f3 and removes the g-pawn from the king\'s shelter. The g-file becomes half-open for White.<br/><br/>Given the question\'s no-immediate-tactic condition, Qxf3 is the straightforward structural choice. In a full game, calculate both: opening a file can sometimes support an attack.',y)
callout('If you missed 05-07','Compare the recapturing piece, the files and the pawn structure. A trade changes more than the material count.',650)

begin('Answers / 08-10','Check how the game ends','The most important consequence of an exchange may be the result itself.')
y=137
y=section('08 / A dead position','<b>1.Rxd8+ Kxd8</b> leaves White with a king and bishop, Black with a king. Checkmate is impossible by any legal continuation, so this is a draw. An extra piece is not enough if the remaining material cannot deliver mate. [1]',y)
y=section('09 / One capture draws, one keeps the win','<b>1.Qxb6?</b> is stalemate. Black\'s king on a8 is not in check. The queen covers b8 and a7; b7 is also covered. There are no other black units to move.<br/><br/><b>1.Kxb6</b> preserves the win. The king on b6 blocks its own queen\'s b-file, leaving <b>1...Kb8</b> legal. White still has king and queen against king. The exact location of the capturing unit changes the result.',y)
y=section('10 / Mate on the back rank','<b>1.Rd8#.</b> The rook attacks g8 along the eighth rank. Black\'s own pawns occupy f7, g7 and h7; f8 and h8 are covered by the rook. The bishop cannot capture the rook or block the check. Capturing the bishop with Rxc1 misses an immediate finish.',y)
y=section('Read your score as feedback','<b>17-20:</b> apply the checklist in slow games and review your exceptions.<br/><b>12-16:</b> repeat the questions from your weakest lesson.<br/><b>0-11:</b> replay each answer on a board, then solve again tomorrow.<br/>This is a study guide, not a rating estimate.',y)

# 20 / reference sheet
begin('Keep beside your board','A repeatable practice routine','Aim for a better decision process. A single correct move is not the whole skill.')
y=136
y=section('Your short capture checklist','<b>SAFE?</b> My king remains legal and secure.<br/><b>REPLY?</b> I checked the opponent\'s checks, captures and threats.<br/><b>COUNT?</b> I counted the full exchange, not just the first capture.<br/><b>REMAINS?</b> I compared activity, structure and the ending.<br/><b>ALTERNATIVE?</b> I considered keeping tension or improving a piece.',y)
y=section('Seven days, about 20 minutes per day','<b>Day 1:</b> method + Lesson 1; do exercises 01-02.<br/><b>Day 2:</b> Lesson 2; do exercises 03-04.<br/><b>Day 3:</b> Lessons 3-4; do exercises 05-06.<br/><b>Day 4:</b> Lesson 5; do exercise 07 and replay both recaptures.<br/><b>Day 5:</b> Lessons 6-8; do exercises 08-10.<br/><b>Day 6:</b> review one slow game; annotate three exchange decisions.<br/><b>Day 7:</b> repeat missed exercises without looking at the answers.',y)
y=section('Review one decision from your own game','Record the position or move number. Write what you expected, what the opponent could do, and what the trade changed. Then replay taking, declining and a quiet alternative. Use analysis tools after writing your own reasoning.',y)
callout('Review note to copy','Move: ___   Candidate: ___   Best reply: ___<br/>Material change: ___   Positional change: ___   Better plan: ___',649,74)

# 21 / credits and further study
begin('Sources / further practice','Keep studying the right questions','Links checked September 12, 2026. Lesson explanations and exercise text were written for this course.')
y=138
y=section('[1] Rules and notation','FIDE, <i>Laws of Chess taking effect from 1 January 2023</i>. Articles 1.4.1 and 3.9.2 cover king safety; 5.2.1 covers stalemate; 5.2.2 covers dead positions; Appendix C covers algebraic notation.<br/><link href="https://handbook.fide.com/chapter/E012023" color="#176F69">handbook.fide.com/chapter/E012023</link>',y)
y=section('[2] Piece-value starting points','Chess.com, <i>How to Play Chess</i>. A reference for standard relative piece values and basic movement rules.<br/><link href="https://www.chess.com/learn-how-to-play-chess" color="#176F69">chess.com/learn-how-to-play-chess</link>',y)
y=section('[3] Intermediate moves','Chess.com, <i>Zwischenzug</i>. Explains making a useful intervening move before an expected response.<br/><link href="https://www.chess.com/terms/zwischenzug-chess" color="#176F69">chess.com/terms/zwischenzug-chess</link>',y)
y=section('Practice the tactical building blocks','Lichess Practice has modules on pins, overloaded pieces, intermediate moves and basic endgames. Choose the topic behind an exercise you missed.<br/><link href="https://lichess.org/practice" color="#176F69">lichess.org/practice</link><br/>For replaying positions: <link href="https://lichess.org/analysis" color="#176F69">lichess.org/analysis</link>.',y)
y=section('Diagrams and validation','Boards use python-chess with Cburnett chess-piece artwork (CC BY-SA 3.0). Artwork attribution: <link href="https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces" color="#176F69">Wikimedia Commons, SVG chess pieces</link>. License: <link href="https://creativecommons.org/licenses/by-sa/3.0/" color="#176F69">creativecommons.org/licenses/by-sa/3.0/</link>.<br/>All printed move sequences were checked for legality. Explicit mate, stalemate and insufficient-material endpoints were checked programmatically. Illustrative lines are not claimed to be exhaustive engine analysis.',y)
para('The companion PGN contains lesson and answer lines. Finish the exercises before opening it.',48,708,516,'small')

c.save()
(OUT/'course.md').write_text('\n\n'.join(markdown)+'\n',encoding='utf-8')
(OUT/'positions-and-answers.pgn').write_text('\n\n'.join(str(g) for g in pgn_games)+'\n',encoding='utf-8')
reader=PdfReader(PDF)
assert len(reader.pages)==21,len(reader.pages)
for n,p in enumerate(reader.pages,1):
    text=p.extract_text()
    assert text and len(text)>100,(n,'missing text')
    assert '\ufffd' not in text,(n,'replacement character')
report={'pages':len(reader.pages),'legal_lines_checked':len(checks),'positions':checks,'pdf_bytes':PDF.stat().st_size}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'pdf':str(PDF),'pages':len(reader.pages),'legal_lines':len(checks),'size_bytes':PDF.stat().st_size}))
